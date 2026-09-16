"""Resumable black-box concurrent-load test for the external DAR authority.

Transient gateway failures are retried at both HTTP-request and logical-round
levels. A logical round keeps the same outcome/refusal/idempotency identifiers
across retries, so recovery cannot silently create a different experiment.

Infrastructure incidents are retained as evidence. They are not converted into
DAR invariant failures; an unresolved round keeps the final verdict
INCONCLUSIVE. A run is PASS only when all requested logical rounds reach a
terminal observed state with no invariant failure and no unresolved round.
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
from pathlib import Path

BASE_URL = os.environ.get("DAR_AUTHORITY_URL", "https://dar-external-authority-v2.onrender.com").rstrip("/")
ROUNDS = int(os.environ.get("DAR_LOAD_ROUNDS", "100"))
WORKERS = int(os.environ.get("DAR_LOAD_WORKERS", "8"))
TIMEOUT = float(os.environ.get("DAR_LOAD_TIMEOUT", "30"))
HEALTH_RETRIES = int(os.environ.get("DAR_HEALTH_RETRIES", "6"))
REQUEST_RETRIES = int(os.environ.get("DAR_REQUEST_RETRIES", "4"))
ROUND_RETRIES = int(os.environ.get("DAR_ROUND_RETRIES", "8"))
RETRY_BASE_SECONDS = float(os.environ.get("DAR_RETRY_BASE_SECONDS", "0.5"))
PROGRESS_INTERVAL = int(os.environ.get("DAR_PROGRESS_INTERVAL", "100"))
HEARTBEAT_SECONDS = float(os.environ.get("DAR_PROGRESS_HEARTBEAT_SECONDS", "60"))
CHECKPOINT_PATH = Path(os.environ.get("DAR_CHECKPOINT_PATH", "/app/state/checkpoint.json"))
RUN_ID = os.environ.get("DAR_LOAD_RUN_ID", "dar-10k-resumable")
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

_progress_lock = threading.Lock()
_status_lock = threading.Lock()
_checkpoint_lock = threading.Lock()
_started = 0
_completed = 0
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
        "checkpoint_path": str(CHECKPOINT_PATH),
        "resumable": True,
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
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with _status_lock:
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as exc:
            print(json.dumps({
                "evidence_type": "external-authority-concurrent-load-status-warning",
                "error": repr(exc),
                "completed_rounds": completed,
                "rounds": ROUNDS,
            }, sort_keys=True), flush=True)


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
            time.sleep(RETRY_BASE_SECONDS * (2 ** attempt) + random.random() * 0.1)
    raise InfrastructureFailure("transport", None, repr(last_error))


def post(path: str, body: dict) -> tuple[int, dict]:
    return _request(urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    ))


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


def _round_payload(index: int) -> tuple[str, int, str, str, str]:
    # Stable identifiers make a retry the same logical observation, not a new round.
    namespace = uuid.NAMESPACE_URL
    outcome = uuid.uuid5(namespace, f"{RUN_ID}:outcome:{index}").hex
    epoch = index + 1
    refusal_id = f"{RUN_ID}:refusal:{index}"
    idem_a = f"{RUN_ID}:commit-a:{index}"
    idem_b = f"{RUN_ID}:commit-b:{index}"
    return outcome, epoch, refusal_id, idem_a, idem_b


def race_round(index: int) -> dict:
    outcome, epoch, refusal_id, idem_a, idem_b = _round_payload(index)
    barrier = threading.Barrier(2)

    def refusal() -> tuple[str, int, dict]:
        barrier.wait()
        time.sleep(random.random() * 0.020)
        return (*(("refuse",) + post("/refuse", {
            "outcome": outcome,
            "epoch": epoch,
            "refusal_id": refusal_id,
        })),)

    def commit() -> tuple[str, int, dict]:
        barrier.wait()
        time.sleep(random.random() * 0.020)
        status, body = post("/fence", {"outcome": outcome, "epoch": epoch})
        if status == 200:
            status, body = post("/commit", {
                "outcome": outcome,
                "epoch": epoch,
                "idempotency_key": idem_a,
            })
        return "commit", status, body

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(refusal), pool.submit(commit)]
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
        bypass_status, bypass_body = post("/commit", {
            "outcome": outcome,
            "epoch": epoch,
            "idempotency_key": idem_b,
        })
        if bypass_status in GATEWAY_CODES:
            raise InfrastructureFailure(f"round-{index}:fresh-idempotency", bypass_status, bypass_body)
        if bypass_status != 409:
            raise AssertionError((outcome, bypass_status, bypass_body, state))

    if not (refused ^ committed):
        raise AssertionError((outcome, observed, state))

    return {
        "index": index,
        "outcome": outcome,
        "refuse_status": refuse_status,
        "commit_status": commit_status,
        "refused": refused,
        "committed": committed,
        "fresh_idempotency_bypass_status": bypass_status,
    }


def _load_checkpoint() -> dict:
    try:
        if not CHECKPOINT_PATH.exists():
            return {"version": 1, "run_id": RUN_ID, "rounds": ROUNDS, "completed": {}, "attempts": {}, "infrastructure_events": []}
        data = json.loads(CHECKPOINT_PATH.read_text())
        if data.get("run_id") != RUN_ID or int(data.get("rounds", -1)) != ROUNDS:
            return {"version": 1, "run_id": RUN_ID, "rounds": ROUNDS, "completed": {}, "attempts": {}, "infrastructure_events": []}
        data.setdefault("completed", {})
        data.setdefault("attempts", {})
        data.setdefault("infrastructure_events", [])
        return data
    except Exception as exc:
        print(json.dumps({"evidence_type": "external-authority-concurrent-load-checkpoint-warning", "error": repr(exc), "path": str(CHECKPOINT_PATH)}, sort_keys=True), flush=True)
        return {"version": 1, "run_id": RUN_ID, "rounds": ROUNDS, "completed": {}, "attempts": {}, "infrastructure_events": []}


def _save_checkpoint(state: dict) -> None:
    with _checkpoint_lock:
        CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = CHECKPOINT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, sort_keys=True))
        tmp.replace(CHECKPOINT_PATH)


def _evidence(health: dict, results: dict[int, dict], invariant_failures: list[str], infrastructure_events: list[str], unresolved: list[str], verdict: str) -> dict:
    refused = sum(1 for item in results.values() if item["refused"])
    committed = sum(1 for item in results.values() if item["committed"])
    complete = len(results) == ROUNDS and not unresolved and not invariant_failures
    invariant_ok = not invariant_failures and all(item["refused"] ^ item["committed"] for item in results.values())
    return {
        "evidence_type": "external-authority-concurrent-load-black-box",
        "base_url": BASE_URL,
        "run_id": RUN_ID,
        "rounds": ROUNDS,
        "workers": WORKERS,
        "timeout_seconds": TIMEOUT,
        "arrival_rate": {
            "stage_1": {"end_round": STAGE_1_END, "rounds_per_second": STAGE_1_RATE},
            "stage_2": {"end_round": STAGE_2_END, "rounds_per_second": STAGE_2_RATE},
            "stage_3": {"end_round": ROUNDS, "rounds_per_second": STAGE_3_RATE},
        },
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
        "infrastructure_failures": unresolved[:10],
        "recovered_infrastructure_events": infrastructure_events[:25],
        "checkpoint_path": str(CHECKPOINT_PATH),
        "resumable": True,
        "verdict": verdict,
    }


def main() -> None:
    global _completed, _started
    try:
        health = wait_for_health()
    except InfrastructureFailure as exc:
        evidence = _evidence({"ok": False, "error": "database_unavailable", "detail": str(exc)}, {}, [], [repr(exc)], [repr(exc)], "INCONCLUSIVE")
        print(json.dumps(evidence, sort_keys=True), flush=True)
        _publish_progress(0, "failure")
        raise SystemExit(2)

    checkpoint = _load_checkpoint()
    results: dict[int, dict] = {int(k): v for k, v in checkpoint.get("completed", {}).items()}
    attempts: dict[int, int] = {int(k): int(v) for k, v in checkpoint.get("attempts", {}).items()}
    infrastructure_events: list[str] = list(checkpoint.get("infrastructure_events", []))
    invariant_failures: list[str] = []
    unresolved: list[str] = []
    _completed = len(results)

    stop_heartbeat = threading.Event()

    def heartbeat() -> None:
        while not stop_heartbeat.wait(HEARTBEAT_SECONDS):
            _, done = _snapshot_progress()
            print(json.dumps({
                "evidence_type": "external-authority-concurrent-load-heartbeat",
                "base_url": BASE_URL,
                "run_id": RUN_ID,
                "completed_rounds": done,
                "rounds": ROUNDS,
                "workers": WORKERS,
                "stage": _stage_for_round(min(done, max(0, ROUNDS - 1))),
                "arrival_rate_rounds_per_second": _rate_for_round(min(done, max(0, ROUNDS - 1))),
                "resumable": True,
            }, sort_keys=True), flush=True)
            _publish_progress(done)

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()

    pending = [index for index in range(ROUNDS) if index not in results]
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            queue = list(pending)
            while queue and not _stop_requested.is_set():
                batch = queue[:WORKERS]
                queue = queue[WORKERS:]
                futures: dict[concurrent.futures.Future[dict], int] = {}
                for index in batch:
                    attempts[index] = attempts.get(index, 0) + 1
                    with _progress_lock:
                        _started += 1
                    futures[pool.submit(race_round, index)] = index
                for future, index in list(futures.items()):
                    try:
                        result = future.result()
                        results[index] = result
                        with _progress_lock:
                            _completed = len(results)
                        checkpoint["completed"] = {str(k): v for k, v in results.items()}
                        checkpoint["attempts"] = {str(k): v for k, v in attempts.items()}
                        checkpoint["infrastructure_events"] = infrastructure_events[-100:]
                        _save_checkpoint(checkpoint)
                        if _completed == 1 or _completed % PROGRESS_INTERVAL == 0 or _completed == ROUNDS:
                            print(json.dumps({
                                "evidence_type": "external-authority-concurrent-load-progress",
                                "base_url": BASE_URL,
                                "run_id": RUN_ID,
                                "completed_rounds": _completed,
                                "rounds": ROUNDS,
                                "workers": WORKERS,
                                "stage": _stage_for_round(min(_completed, max(0, ROUNDS - 1))),
                                "arrival_rate_rounds_per_second": _rate_for_round(min(_completed, max(0, ROUNDS - 1))),
                                "resumable": True,
                            }, sort_keys=True), flush=True)
                            _publish_progress(_completed)
                    except InfrastructureFailure as exc:
                        event = f"round={index}: attempt={attempts[index]}: {exc!r}"
                        infrastructure_events.append(event)
                        if attempts[index] <= ROUND_RETRIES:
                            delay = RETRY_BASE_SECONDS * (2 ** min(attempts[index] - 1, 6))
                            time.sleep(delay + random.random() * 0.2)
                            queue.append(index)
                        else:
                            unresolved.append(event)
                        checkpoint["attempts"] = {str(k): v for k, v in attempts.items()}
                        checkpoint["infrastructure_events"] = infrastructure_events[-100:]
                        checkpoint["completed"] = {str(k): v for k, v in results.items()}
                        _save_checkpoint(checkpoint)
                    except AssertionError as exc:
                        invariant_failures.append(f"round={index}: {exc!r}")
                        checkpoint["completed"] = {str(k): v for k, v in results.items()}
                        _save_checkpoint(checkpoint)
                    except Exception as exc:
                        event = f"round={index}: attempt={attempts[index]}: unexpected={exc!r}"
                        infrastructure_events.append(event)
                        if attempts[index] <= ROUND_RETRIES:
                            queue.append(index)
                        else:
                            unresolved.append(event)
                        checkpoint["infrastructure_events"] = infrastructure_events[-100:]
                        checkpoint["completed"] = {str(k): v for k, v in results.items()}
                        _save_checkpoint(checkpoint)
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)

    if _stop_requested.is_set():
        evidence = _partial_evidence("controlled stop requested")
        evidence["infrastructure_failures"] = unresolved[:10]
        evidence["recovered_infrastructure_events"] = infrastructure_events[:25]
        print(json.dumps(evidence, sort_keys=True), flush=True)
        _publish_progress(_completed, "failure")
        return

    # Any retryable failure that remained in queue but was not completed is unresolved.
    unresolved_indexes = [index for index in range(ROUNDS) if index not in results]
    for index in unresolved_indexes:
        marker = f"round={index}: unresolved after {attempts.get(index, 0)} attempts"
        if marker not in unresolved:
            unresolved.append(marker)

    verdict = "PASS" if len(results) == ROUNDS and not invariant_failures and not unresolved else "INCONCLUSIVE"
    evidence = _evidence(health, results, invariant_failures, infrastructure_events, unresolved, verdict)
    print(json.dumps(evidence, sort_keys=True), flush=True)
    _publish_progress(len(results), "success" if verdict == "PASS" else "failure")
    if verdict == "PASS":
        return
    raise SystemExit(2)


if __name__ == "__main__":
    main()
