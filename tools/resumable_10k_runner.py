"""Portable, checkpointed launcher for the DAR 10K external-load test.

The underlying black-box test remains the source of truth. This launcher adds
restart-safe orchestration: completed round results are atomically checkpointed
to a configurable local path and resumed after interruption. Transient gateway
failures are re-queued instead of being silently dropped, which prevents the
old 1770/10000 termination mode.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import signal
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import tests.test_external_load as harness

CHECKPOINT = Path(os.environ.get("DAR_CHECKPOINT_PATH", "/app/state/checkpoint.json"))
CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
CHECKPOINT_LOCK = threading.Lock()
ROUND_RETRIES = int(os.environ.get("DAR_ROUND_RETRIES", "8"))
RETRY_BASE_SECONDS = float(os.environ.get("DAR_RETRY_BASE_SECONDS", "0.5"))
_stop_requested = threading.Event()
_signal_name: str | None = None


def _checkpoint_payload(results: dict[int, dict]) -> dict:
    return {
        "schema": 1,
        "rounds_total": harness.ROUNDS,
        "completed_rounds": len(results),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "results": [{"index": i, **results[i]} for i in sorted(results)],
    }


def _save_checkpoint(results: dict[int, dict]) -> None:
    payload = json.dumps(_checkpoint_payload(results), sort_keys=True, indent=2) + "\n"
    with CHECKPOINT_LOCK:
        CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="checkpoint.", suffix=".tmp", dir=CHECKPOINT.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, CHECKPOINT)
        finally:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass


def _load_checkpoint() -> dict[int, dict]:
    if not CHECKPOINT.exists():
        return {}
    try:
        data = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or int(data.get("rounds_total", -1)) != harness.ROUNDS:
            return {}
        loaded: dict[int, dict] = {}
        for item in data.get("results", []):
            index = int(item["index"])
            if 0 <= index < harness.ROUNDS:
                item = dict(item)
                item.pop("index", None)
                loaded[index] = item
        return loaded
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return {}


def _clear_checkpoint() -> None:
    try:
        CHECKPOINT.unlink()
    except FileNotFoundError:
        pass


def _handle_signal(signum: int, _frame) -> None:
    global _signal_name
    _signal_name = signal.Signals(signum).name
    _stop_requested.set()


for _sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(_sig, _handle_signal)


def main() -> None:
    loaded = _load_checkpoint()
    if loaded:
        harness._completed = len(loaded)
        harness._started = len(loaded)
        print(json.dumps({
            "evidence_type": "external-authority-concurrent-load-resume",
            "checkpoint": str(CHECKPOINT),
            "resumed_rounds": len(loaded),
            "rounds": harness.ROUNDS,
            "remaining_rounds": harness.ROUNDS - len(loaded),
        }, sort_keys=True), flush=True)

    try:
        health = harness.wait_for_health()
    except harness.InfrastructureFailure as exc:
        evidence = harness._evidence(
            {"ok": False, "error": "database_unavailable", "detail": str(exc)},
            list(loaded.values()), [], [repr(exc)], "INCONCLUSIVE"
        )
        print(json.dumps(evidence, sort_keys=True), flush=True)
        raise SystemExit(2)

    results = dict(loaded)
    invariant_failures: list[str] = []
    infrastructure_events: list[str] = []
    unresolved_failures: list[str] = []
    attempts: dict[int, int] = {}
    in_flight: dict[concurrent.futures.Future[dict], int] = {}
    retry_queue: list[int] = []
    next_launch_at = time.monotonic()
    next_index = 0
    stop_heartbeat = threading.Event()
    harness._publish_progress(len(results))

    def heartbeat() -> None:
        while not stop_heartbeat.wait(harness.HEARTBEAT_SECONDS):
            done = len(results)
            print(json.dumps({
                "evidence_type": "external-authority-concurrent-load-heartbeat",
                "base_url": harness.BASE_URL,
                "completed_rounds": done,
                "rounds": harness.ROUNDS,
                "workers": harness.WORKERS,
                "stage": harness._stage_for_round(min(done, max(0, harness.ROUNDS - 1))),
                "arrival_rate_rounds_per_second": harness._rate_for_round(min(done, max(0, harness.ROUNDS - 1))),
                "resumable": True,
            }, sort_keys=True), flush=True)
            harness._publish_progress(done)

    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=harness.WORKERS) as pool:
            while next_index < harness.ROUNDS or retry_queue or in_flight:
                if _stop_requested.is_set():
                    break

                # Prefer retries so a transiently failed logical round is closed
                # before the run advances too far.
                while next_index < harness.ROUNDS and next_index in results:
                    next_index += 1

                while len(in_flight) < harness.WORKERS and (retry_queue or next_index < harness.ROUNDS):
                    if retry_queue:
                        index = retry_queue.pop(0)
                    else:
                        index = next_index
                        next_index += 1
                        while next_index < harness.ROUNDS and next_index in results:
                            next_index += 1

                    if index in results:
                        continue
                    attempts[index] = attempts.get(index, 0) + 1
                    future = pool.submit(harness.race_round, index)
                    in_flight[future] = index
                    if not retry_queue and index >= next_index:
                        next_index = index + 1

                    rate = harness._rate_for_round(index)
                    now = time.monotonic()
                    next_launch_at = max(next_launch_at, now) + (1.0 / rate)
                    if len(in_flight) >= harness.WORKERS:
                        break

                if not in_flight:
                    if retry_queue:
                        continue
                    if next_index >= harness.ROUNDS:
                        break
                    if time.monotonic() < next_launch_at:
                        time.sleep(min(next_launch_at - time.monotonic(), 0.25))
                    continue

                done, _ = concurrent.futures.wait(
                    in_flight, timeout=0.5, return_when=concurrent.futures.FIRST_COMPLETED
                )
                for future in done:
                    index = in_flight.pop(future)
                    try:
                        results[index] = future.result()
                        harness._completed = len(results)
                        _save_checkpoint(results)
                        if len(results) == 1 or len(results) % harness.PROGRESS_INTERVAL == 0 or len(results) == harness.ROUNDS:
                            print(json.dumps({
                                "evidence_type": "external-authority-concurrent-load-progress",
                                "base_url": harness.BASE_URL,
                                "completed_rounds": len(results),
                                "rounds": harness.ROUNDS,
                                "workers": harness.WORKERS,
                                "stage": harness._stage_for_round(min(len(results), max(0, harness.ROUNDS - 1))),
                                "arrival_rate_rounds_per_second": harness._rate_for_round(min(len(results), max(0, harness.ROUNDS - 1))),
                                "resumable": True,
                            }, sort_keys=True), flush=True)
                            harness._publish_progress(len(results))
                    except harness.InfrastructureFailure as exc:
                        event = f"round={index}: attempt={attempts.get(index, 1)}: {exc!r}"
                        infrastructure_events.append(event)
                        if attempts.get(index, 1) <= ROUND_RETRIES:
                            retry_queue.append(index)
                            delay = RETRY_BASE_SECONDS * (2 ** min(attempts.get(index, 1) - 1, 6))
                            time.sleep(delay)
                            print(json.dumps({
                                "evidence_type": "external-authority-concurrent-load-retry",
                                "round": index,
                                "attempt": attempts.get(index, 1),
                                "retry_in_seconds": delay,
                                "completed_rounds": len(results),
                                "resumable": True,
                            }, sort_keys=True), flush=True)
                        else:
                            unresolved_failures.append(event)
                        _save_checkpoint(results)
                    except AssertionError as exc:
                        invariant_failures.append(f"round={index}: {exc!r}")
                        _save_checkpoint(results)
                    except Exception as exc:
                        event = f"round={index}: attempt={attempts.get(index, 1)}: unexpected={exc!r}"
                        infrastructure_events.append(event)
                        if attempts.get(index, 1) <= ROUND_RETRIES:
                            retry_queue.append(index)
                        else:
                            unresolved_failures.append(event)
                        _save_checkpoint(results)
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)
        if results and len(results) < harness.ROUNDS:
            _save_checkpoint(results)

    if _stop_requested.is_set():
        evidence = harness._partial_evidence(f"controlled stop requested; checkpoint={CHECKPOINT}")
        evidence["completed_rounds"] = len(results)
        evidence["remaining_rounds"] = harness.ROUNDS - len(results)
        evidence["infrastructure_failures"] = unresolved_failures[:10]
        evidence["invariant_failures"] = invariant_failures[:10]
        evidence["recovered_infrastructure_events"] = infrastructure_events[:25]
        print(json.dumps(evidence, sort_keys=True), flush=True)
        harness._publish_progress(len(results), "failure")
        raise SystemExit(2)

    unresolved_indexes = [index for index in range(harness.ROUNDS) if index not in results]
    for index in unresolved_indexes:
        marker = f"round={index}: unresolved after {attempts.get(index, 0)} attempts"
        if marker not in unresolved_failures:
            unresolved_failures.append(marker)

    if invariant_failures:
        verdict, exit_code = "FAIL", 1
    elif unresolved_failures or len(results) != harness.ROUNDS:
        verdict, exit_code = "INCONCLUSIVE", 2
    else:
        refused = sum(1 for item in results.values() if item["refused"])
        committed = sum(1 for item in results.values() if item["committed"])
        if refused + committed != harness.ROUNDS:
            invariant_failures.append(f"winner accounting mismatch: refused={refused} committed={committed}")
            verdict, exit_code = "FAIL", 1
        else:
            verdict, exit_code = "PASS", 0

    ordered = [results[i] for i in sorted(results)]
    evidence = harness._evidence(health, ordered, invariant_failures, unresolved_failures, verdict)
    evidence["resumable"] = True
    evidence["checkpoint_path"] = str(CHECKPOINT)
    evidence["recovered_infrastructure_events"] = infrastructure_events[:25]
    print(json.dumps(evidence, sort_keys=True), flush=True)
    harness._publish_progress(len(results), "success" if verdict == "PASS" else "failure")
    if verdict == "PASS":
        _clear_checkpoint()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
