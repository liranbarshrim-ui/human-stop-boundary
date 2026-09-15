"""Black-box concurrent-load test for the external DAR authority.

The harness distinguishes DAR invariant failures from infrastructure failures.
A transport/database outage is INCONCLUSIVE, not a DAR FAIL.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import random
import signal
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
GITHUB_TOKEN = os.environ.get("DAR_HEARTBEAT_GITHUB_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GITHUB_SHA = os.environ.get("GITHUB_SHA")
STATUS_CONTEXT = "DAR / 10K-B progress"
STAGE_1_END = int(os.environ.get("DAR_STAGE_1_END", "1000"))
STAGE_2_END = int(os.environ.get("DAR_STAGE_2_END", "4000"))
STAGE_1_RATE = float(os.environ.get("DAR_STAGE_1_RATE", "1.0"))
STAGE_2_RATE = float(os.environ.get("DAR_STAGE_2_RATE", "2.0"))
STAGE_3_RATE = float(os.environ.get("DAR_STAGE_3_RATE", "3.0"))
_status_lock = threading.Lock()
_progress_lock = threading.Lock()
_completed = 0
_started = 0
_stop_requested = threading.Event()
_signal_name: str | None = None


class InfrastructureFailure(RuntimeError):
    """The system could not complete an observation because infrastructure failed."""

    def __init__(self, operation: str, status: int | None, body: object):
        self.operation = operation
        self.status = status
        self.body = body
        super().__init__(f"infrastructure failure during {operation}: status={status} body={body!r}")


def _rate_for_round(index: int) -> float:
    if index < STAGE_1_END:
        return STAGE_1_RATE
    if index < STAGE_2_END:
        return STAGE_2_RATE
    return STAGE_3_RATE


def _stage_for_round(index: int) -> str:
    if index < STAGE_1_END:
        return "stage-1"
    if index < STAGE_2_END:
        return "stage-2"
    return "stage-3"


def _snapshot_progress() -> tuple[int, int]:
    with _progress_lock:
        return _started, _completed


def _partial_evidence(reason: str) -> dict:
    started, completed = _snapshot_progress()
    return {
        "evidence_type": "external-authority-concurrent-load-partial",
        "base_url": BASE_URL,
        "rounds": ROUNDS,
        "workers": WORKERS,
        "timeout_seconds": TIMEOUT,
        "arrival_rate": {
            "stage_1": {"end_round": STAGE_1_END, "rounds_per_second": STAGE_1_RATE},
            "stage_2": {"end_round": STAGE_2_END, "rounds_per_second": STAGE_2_RATE},
            "stage_3": {"end_round": ROUNDS, "rounds_per_second": STAGE_3_RATE},
        },
        "started_rounds": started,
        "completed_rounds": completed,
        "remaining_rounds": max(0, ROUNDS - completed),
        "reason": reason,
        "signal": _signal_name,
        "verdict": "INCONCLUSIVE",
    }


def _handle_signal(signum: int, _frame) -> None:
    global _signal_name
    _signal_name = signal.Signals(signum).name
    _stop_requested.set()
    print(json.dumps(_partial_evidence(f"received {_signal_name}"), sort_keys=True), flush=True)


for _sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(_sig, _handle_signal)


def _publish_progress(completed: int, state: str = "pending") -> None:
    if not (GITHUB_TOKEN and GITHUB_REPOSITORY and GITHUB_SHA):
        return
    description = f"10K-B progress: {completed}/{ROUNDS} rounds completed"
    if state == "success":
        description = f"10K-B PASS: {completed}/{ROUNDS} rounds completed"
    elif state == "failure":
        description = f"10K-B INCONCLUSIVE: {completed}/{ROUNDS} rounds completed"
    body = json.dumps({
        "state": state,
        "target_url": f"https://github.com/{GITHUB_REPOSITORY}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
        "description": description[:140],
        "context": STATUS_CONTEXT,
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPOSITORY}/statuses/{GITHUB_SHA}",
        data=body,
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"},
        method="POST",
    )
    with _status_lock:
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as exc:
            print(json.dumps({"evidence_type": "external-authority-concurrent-load-status-warning", "error": repr(exc), "completed_rounds": completed, "rounds": ROUNDS}, sort_keys=True), flush=True)


def _request(req: urllib.request.Request) -> tuple[int, dict]:
    last_error: Exception | None = None
    for attempt in range(REQUEST_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read())
            except Exception:
                body = {"error": exc.reason}
            if exc.code not in GATEWAY_CODES or attempt >= REQUEST_RETRIES:
                return exc.code, body
            last_error = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt >= REQUEST_RETRIES:
                raise InfrastructureFailure("transport", None, repr(exc)) from exc
            last_error = exc
        if attempt < REQUEST_RETRIES:
            time.sleep(0.5 * (2 ** attempt))
    raise InfrastructureFailure("transport", None, repr(last_error))


def post(path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(BASE_URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    return _request(req)


def get(path: str) -> tuple[int, dict]:
    return _request(urllib.request.Request(BASE_URL + path, method="GET"))


def _require_usable(status: int, body: dict, operation: str) -> dict:
    if status in GATEWAY_CODES:
        raise InfrastructureFailure(operation, status, body)
    return body


def wait_for_health() -> dict:
    last_error: Exception | None = None
    for attempt in range(HEALTH_RETRIES):
        try:
            status, health = get("/health")
            if status == 200 and health.get("ok") is True and health.get("persistence") == "postgres":
                return health
            last_error = InfrastructureFailure("health", status, health)
        except InfrastructureFailure as exc:
            last_error = exc
        except Exception as exc:
            last_error = InfrastructureFailure("health", None, repr(exc))
        if attempt + 1 < HEALTH_RETRIES:
            time.sleep(2 ** attempt)
    raise InfrastructureFailure("health", getattr(last_error, "status", None), str(last_error))


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

    for name, status, body in observed:
        if status in GATEWAY_CODES:
            raise InfrastructureFailure(f"round-{index}:{name}", status, body)

    _, refuse_status, _ = observed[0]
    _, commit_status, _ = observed[1]
    state_status, state_body = get("/state")
    state = _require_usable(state_status, state_body, f"round-{index}:state")
    refused = outcome in state.get("refusals", {})
    committed = outcome in state.get("committed_outcomes", {})
    if refused and committed:
        raise AssertionError((outcome, observed, state))

    bypass_status = None
    if refused:
        bypass_status, bypass_body = post("/commit", {"outcome": outcome, "epoch": epoch, "idempotency_key": idem_b})
        if bypass_status in GATEWAY_CODES:
            raise InfrastructureFailure(f"round-{index}:fresh-idempotency", bypass_status, bypass_body)
        if bypass_status != 409:
            raise AssertionError((outcome, bypass_status, bypass_body, state))

    return {"outcome": outcome, "refuse_status": refuse_status, "commit_status": commit_status, "refused": refused, "committed": committed, "fresh_idempotency_bypass_status": bypass_status}


def _evidence(health: dict, results: list[dict], invariant_failures: list[str], infrastructure_failures: list[str], verdict: str) -> dict:
    refused = sum(1 for item in results if item["refused"])
    committed = sum(1 for item in results if item["committed"])
    complete = len(results) == ROUNDS and not infrastructure_failures
    invariant_ok = not invariant_failures and all(item["refused"] ^ item["committed"] for item in results)
    return {
        "evidence_type": "external-authority-concurrent-load-black-box",
        "base_url": BASE_URL,
        "rounds": ROUNDS,
        "workers": WORKERS,
        "timeout_seconds": TIMEOUT,
        "arrival_rate": {"stage_1": {"end_round": STAGE_1_END, "rounds_per_second": STAGE_1_RATE}, "stage_2": {"end_round": STAGE_2_END, "rounds_per_second": STAGE_2_RATE}, "stage_3": {"end_round": ROUNDS, "rounds_per_second": STAGE_3_RATE}},
        "health": health,
        "completed_rounds": len(results),
        "refused_rounds": refused,
        "committed_rounds": committed,
        "checks": {
            "health_postgres": "PASS",
            "concurrent_refusal_commit_exclusion": "PASS" if invariant_ok else "FAIL",
            "no_both_winners": "PASS" if invariant_ok else "FAIL",
            "fresh_idempotency_key_cannot_bypass_refusal": "PASS" if invariant_ok else "FAIL",
            "all_rounds_completed": "PASS" if complete else "INCONCLUSIVE",
        },
        "invariant_failures": invariant_failures[:10],
        "infrastructure_failures": infrastructure_failures[:10],
        "verdict": verdict,
    }


def main() -> None:
    global _completed, _started
    try:
        health = wait_for_health()
    except InfrastructureFailure as exc:
        evidence = _evidence({"ok": False, "error": "database_unavailable", "detail": str(exc)}, [], [], [repr(exc)], "INCONCLUSIVE")
        print(json.dumps(evidence, sort_keys=True), flush=True)
        _publish_progress(0, "failure")
        raise SystemExit(2)

    results: list[dict] = []
    invariant_failures: list[str] = []
    infrastructure_failures: list[str] = []
    next_index = 0
    in_flight: dict[concurrent.futures.Future[dict], int] = {}
    next_launch_at = time.monotonic()
    stop_heartbeat = threading.Event()
    _publish_progress(0)

    def heartbeat() -> None:
        while not stop_heartbeat.wait(HEARTBEAT_SECONDS):
            _, done = _snapshot_progress()
            print(json.dumps({"evidence_type": "external-authority-concurrent-load-heartbeat", "base_url": BASE_URL, "completed_rounds": done, "rounds": ROUNDS, "workers": WORKERS, "stage": _stage_for_round(done), "arrival_rate_rounds_per_second": _rate_for_round(done)}, sort_keys=True), flush=True)
            _publish_progress(done)

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            while next_index < ROUNDS or in_flight:
                if _stop_requested.is_set():
                    break
                if next_index < ROUNDS and len(in_flight) < WORKERS:
                    now = time.monotonic()
                    if now < next_launch_at:
                        time.sleep(min(next_launch_at - now, 0.25))
                        continue
                    rate = _rate_for_round(next_index)
                    future = pool.submit(race_round, next_index)
                    in_flight[future] = next_index
                    with _progress_lock:
                        _started += 1
                    next_index += 1
                    next_launch_at = max(next_launch_at, now) + (1.0 / rate)
                    continue
                if not in_flight:
                    continue
                done, _ = concurrent.futures.wait(in_flight, timeout=0.5, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    index = in_flight.pop(future)
                    try:
                        results.append(future.result())
                        with _progress_lock:
                            _completed = len(results)
                        if _completed == 1 or _completed % PROGRESS_INTERVAL == 0 or _completed == ROUNDS:
                            print(json.dumps({"evidence_type": "external-authority-concurrent-load-progress", "base_url": BASE_URL, "completed_rounds": _completed, "rounds": ROUNDS, "workers": WORKERS, "stage": _stage_for_round(_completed), "arrival_rate_rounds_per_second": _rate_for_round(_completed)}, sort_keys=True), flush=True)
                            _publish_progress(_completed)
                    except InfrastructureFailure as exc:
                        infrastructure_failures.append(f"round={index}: {exc!r}")
                    except AssertionError as exc:
                        invariant_failures.append(f"round={index}: {exc!r}")
                    except Exception as exc:
                        infrastructure_failures.append(f"round={index}: unexpected={exc!r}")
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)

    if _stop_requested.is_set():
        evidence = _partial_evidence("controlled stop requested")
        evidence["infrastructure_failures"] = infrastructure_failures[:10]
        evidence["invariant_failures"] = invariant_failures[:10]
        print(json.dumps(evidence, sort_keys=True), flush=True)
        _publish_progress(len(results), "failure")
        raise SystemExit(2)

    if invariant_failures:
        verdict, exit_code = "FAIL", 1
    elif infrastructure_failures or len(results) != ROUNDS:
        verdict, exit_code = "INCONCLUSIVE", 2
    else:
        refused = sum(1 for item in results if item["refused"])
        committed = sum(1 for item in results if item["committed"])
        if refused + committed != ROUNDS:
            invariant_failures.append(f"winner accounting mismatch: refused={refused} committed={committed}")
            verdict, exit_code = "FAIL", 1
        else:
            verdict, exit_code = "PASS", 0

    evidence = _evidence(health, results, invariant_failures, infrastructure_failures, verdict)
    print(json.dumps(evidence, sort_keys=True), flush=True)
    _publish_progress(len(results), "success" if verdict == "PASS" else "failure")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
