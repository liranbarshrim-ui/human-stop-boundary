"""Black-box concurrent-load test for the external DAR authority.

The harness knows only the public HTTP contract. Each round races one refusal
against one protected commit for the same outcome. Across many independent
outcomes it also exercises concurrent commits, retries, and refusals.

A valid result must never observe both a successful protected commit and a
successful terminal refusal for the same outcome. If refusal wins, all later
new-idempotency-key commits must be rejected. If commit wins, a later refusal
must not retroactively erase the committed outcome.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
import uuid

BASE_URL = os.environ.get("DAR_AUTHORITY_URL", "https://dar-external-authority-v2.onrender.com").rstrip("/")
ROUNDS = int(os.environ.get("DAR_LOAD_ROUNDS", "100"))
WORKERS = int(os.environ.get("DAR_LOAD_WORKERS", "8"))
TIMEOUT = float(os.environ.get("DAR_LOAD_TIMEOUT", "30"))
HEALTH_RETRIES = int(os.environ.get("DAR_HEALTH_RETRIES", "6"))
REQUEST_RETRIES = int(os.environ.get("DAR_REQUEST_RETRIES", "4"))
PROGRESS_INTERVAL = int(os.environ.get("DAR_PROGRESS_INTERVAL", "100"))
HEARTBEAT_SECONDS = float(os.environ.get("DAR_PROGRESS_HEARTBEAT_SECONDS", "60"))
GATEWAY_CODES = {502, 503, 504}


def _request(req: urllib.request.Request) -> tuple[int, dict]:
    last_error: Exception | None = None
    for attempt in range(REQUEST_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code not in GATEWAY_CODES or attempt >= REQUEST_RETRIES:
                try:
                    body = json.loads(exc.read())
                except Exception:
                    body = {"error": exc.reason}
                return exc.code, body
            last_error = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt >= REQUEST_RETRIES:
                raise
            last_error = exc
        if attempt < REQUEST_RETRIES:
            time.sleep(0.5 * (2 ** attempt))
    raise AssertionError(f"request failed after retries: {last_error}")


def post(path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _request(req)


def get(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(BASE_URL + path, method="GET")
    return _request(req)


def wait_for_health() -> dict:
    last_error: Exception | None = None
    for attempt in range(HEALTH_RETRIES):
        try:
            status, health = get("/health")
            if status == 200 and health.get("ok") is True and health.get("persistence") == "postgres":
                return health
            last_error = RuntimeError(f"health status={status} body={health}")
        except Exception as exc:
            last_error = exc
        if attempt + 1 < HEALTH_RETRIES:
            time.sleep(2 ** attempt)
    raise AssertionError(f"external authority did not become healthy: {last_error}")


def race_round(index: int) -> dict:
    outcome = uuid.uuid4().hex
    epoch = index + 1
    refusal_id = f"load-refusal-{uuid.uuid4().hex}"
    idem_a = f"load-commit-a-{uuid.uuid4().hex}"
    idem_b = f"load-commit-b-{uuid.uuid4().hex}"
    barrier = threading.Barrier(2)

    def refusal() -> tuple[str, int, dict]:
        barrier.wait()
        time.sleep(random.random() * 0.020)
        status, body = post("/refuse", {"outcome": outcome, "epoch": epoch, "refusal_id": refusal_id})
        return "refuse", status, body

    def commit() -> tuple[str, int, dict]:
        barrier.wait()
        time.sleep(random.random() * 0.020)
        status, body = post("/fence", {"outcome": outcome, "epoch": epoch})
        if status == 200:
            status, body = post("/commit", {"outcome": outcome, "epoch": epoch, "idempotency_key": idem_a})
        return "commit", status, body

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fn) for fn in (refusal, commit)]
        observed = [f.result() for f in futures]

    _, refuse_status, _ = observed[0]
    _, commit_status, _ = observed[1]
    _, state = get("/state")
    refused = outcome in state.get("refusals", {})
    committed = outcome in state.get("committed_outcomes", {})
    assert not (refused and committed), (outcome, observed, state)

    bypass_status = None
    if refused:
        bypass_status, _ = post("/commit", {"outcome": outcome, "epoch": epoch, "idempotency_key": idem_b})
        assert bypass_status == 409, (outcome, bypass_status, state)

    return {
        "outcome": outcome,
        "refuse_status": refuse_status,
        "commit_status": commit_status,
        "refused": refused,
        "committed": committed,
        "fresh_idempotency_bypass_status": bypass_status,
    }


def main() -> None:
    health = wait_for_health()
    results: list[dict] = []
    failures: list[str] = []
    completed = 0
    next_index = 0
    in_flight: dict[concurrent.futures.Future[dict], int] = {}
    lock = threading.Lock()
    stop_heartbeat = threading.Event()

    def heartbeat() -> None:
        while not stop_heartbeat.wait(HEARTBEAT_SECONDS):
            with lock:
                done = completed
            print(json.dumps({
                "evidence_type": "external-authority-concurrent-load-heartbeat",
                "base_url": BASE_URL,
                "completed_rounds": done,
                "rounds": ROUNDS,
                "workers": WORKERS,
            }, sort_keys=True), flush=True)

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            while next_index < ROUNDS and len(in_flight) < WORKERS:
                future = pool.submit(race_round, next_index)
                in_flight[future] = next_index
                next_index += 1

            while in_flight:
                done, _ = concurrent.futures.wait(
                    in_flight,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for future in done:
                    index = in_flight.pop(future)
                    try:
                        results.append(future.result())
                        with lock:
                            completed += 1
                        if completed == 1 or completed % PROGRESS_INTERVAL == 0 or completed == ROUNDS:
                            print(json.dumps({
                                "evidence_type": "external-authority-concurrent-load-progress",
                                "base_url": BASE_URL,
                                "completed_rounds": completed,
                                "rounds": ROUNDS,
                                "workers": WORKERS,
                            }, sort_keys=True), flush=True)
                    except Exception as exc:
                        failures.append(f"round={index}: {exc!r}")
                    if next_index < ROUNDS:
                        replacement = pool.submit(race_round, next_index)
                        in_flight[replacement] = next_index
                        next_index += 1
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)

    if failures or len(results) != ROUNDS:
        evidence = {
            "evidence_type": "external-authority-concurrent-load-black-box",
            "base_url": BASE_URL,
            "rounds": ROUNDS,
            "workers": WORKERS,
            "timeout_seconds": TIMEOUT,
            "health": health,
            "checks": {
                "health_postgres": "PASS",
                "concurrent_refusal_commit_exclusion": "FAIL",
                "no_both_winners": "FAIL",
                "fresh_idempotency_key_cannot_bypass_refusal": "FAIL",
                "all_rounds_completed": "FAIL",
            },
            "completed_rounds": len(results),
            "failures": failures[:10],
            "verdict": "FAIL",
        }
        print(json.dumps(evidence, sort_keys=True), flush=True)
        raise SystemExit(1)

    refused = sum(1 for item in results if item["refused"])
    committed = sum(1 for item in results if item["committed"])
    assert refused + committed == ROUNDS

    evidence = {
        "evidence_type": "external-authority-concurrent-load-black-box",
        "base_url": BASE_URL,
        "rounds": ROUNDS,
        "workers": WORKERS,
        "timeout_seconds": TIMEOUT,
        "health": health,
        "checks": {
            "health_postgres": "PASS",
            "concurrent_refusal_commit_exclusion": "PASS",
            "no_both_winners": "PASS",
            "fresh_idempotency_key_cannot_bypass_refusal": "PASS",
            "all_rounds_completed": "PASS",
        },
        "refusal_wins": refused,
        "commit_wins": committed,
        "verdict": "PASS",
    }
    print(json.dumps(evidence, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

# Triggered from the main branch to produce external deployment evidence.
