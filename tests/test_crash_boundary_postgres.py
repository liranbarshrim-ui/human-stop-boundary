"""Five-scenario crash-boundary evidence against real PostgreSQL.

The child process is killed with SIGKILL at controlled transaction boundaries;
the database is then queried from a fresh process. Scenario 5 verifies
transaction atomicity at the database boundary: an uncommitted partial
transaction cannot be observed after recovery. It does not claim a physical
disk-sector write was interrupted.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg.rows import dict_row

DSN = os.environ["DATABASE_URL"]
PYTHON = sys.executable


def connect():
    return psycopg.connect(DSN, row_factory=dict_row, sslmode="require")


def cleanup(prefix: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM dar_refusals WHERE outcome_key LIKE %s", (prefix + "%",))
        conn.execute("DELETE FROM dar_effects WHERE outcome_key LIKE %s", (prefix + "%",))
        conn.execute("DELETE FROM dar_fences WHERE outcome_key LIKE %s", (prefix + "%",))


def state(outcome: str):
    with connect() as conn:
        refusal = conn.execute("SELECT epoch, refusal_id FROM dar_refusals WHERE outcome_key=%s", (outcome,)).fetchone()
        effect = conn.execute("SELECT idempotency_key, epoch FROM dar_effects WHERE outcome_key=%s", (outcome,)).fetchone()
        fence = conn.execute("SELECT fence FROM dar_fences WHERE outcome_key=%s", (outcome,)).fetchone()
        return {"refusal": refusal, "effect": effect, "fence": fence}


def worker(mode: str, outcome: str, epoch: int, ident: str) -> None:
    if mode == "refusal-before-client-persist":
        with connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (outcome,))
            conn.execute("INSERT INTO dar_fences(outcome_key, fence) VALUES (%s,%s) ON CONFLICT (outcome_key) DO UPDATE SET fence=EXCLUDED.fence", (outcome, epoch))
            conn.execute("INSERT INTO dar_refusals(outcome_key, epoch, refusal_id) VALUES (%s,%s,%s)", (outcome, epoch, ident))
        print("EXTERNAL_REFUSAL_COMMITTED", flush=True)
        time.sleep(300)
    elif mode == "commit-before-client-persist":
        with connect() as conn:
            conn.execute("INSERT INTO dar_fences(outcome_key, fence) VALUES (%s,%s) ON CONFLICT (outcome_key) DO UPDATE SET fence=EXCLUDED.fence", (outcome, epoch))
            conn.execute("INSERT INTO dar_effects(idempotency_key, outcome_key, epoch) VALUES (%s,%s,%s)", (ident, outcome, epoch))
        print("EXTERNAL_COMMIT_COMMITTED", flush=True)
        time.sleep(300)
    elif mode == "torn-write":
        with connect() as conn:
            conn.execute("BEGIN")
            conn.execute("INSERT INTO dar_fences(outcome_key, fence) VALUES (%s,%s)", (outcome, epoch))
            conn.execute("INSERT INTO dar_refusals(outcome_key, epoch, refusal_id) VALUES (%s,%s,%s)", (outcome, epoch, ident))
            print("TORN_WRITE_WINDOW", flush=True)
            time.sleep(300)
    else:
        raise SystemExit(f"unknown worker mode {mode}")


def kill_after_marker(mode: str, outcome: str, epoch: int, ident: str) -> None:
    env = dict(os.environ)
    env["CRASH_BOUNDARY_WORKER"] = "1"
    code = "from tests.test_crash_boundary_postgres import worker; " + f"worker({mode!r}, {outcome!r}, {epoch!r}, {ident!r})"
    proc = subprocess.Popen([PYTHON, "-c", code], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 30
    marker = {
        "refusal-before-client-persist": "EXTERNAL_REFUSAL_COMMITTED",
        "commit-before-client-persist": "EXTERNAL_COMMIT_COMMITTED",
        "torn-write": "TORN_WRITE_WINDOW",
    }[mode]
    while time.time() < deadline:
        line = proc.stdout.readline()
        if marker in line:
            proc.kill()
            proc.wait(timeout=10)
            assert proc.returncode == -signal.SIGKILL, proc.returncode
            return
    proc.kill()
    stderr = proc.stderr.read()
    proc.wait(timeout=10)
    raise AssertionError(f"worker did not reach crash boundary: {stderr}")


def scenario_1() -> None:
    outcome = "crash1-" + uuid.uuid4().hex
    kill_after_marker("refusal-before-client-persist", outcome, 100, "refusal-" + uuid.uuid4().hex)
    s = state(outcome)
    assert s["refusal"] is not None, s
    assert s["effect"] is None, s
    cleanup(outcome)


def scenario_2() -> None:
    outcome = "crash2-" + uuid.uuid4().hex
    kill_after_marker("commit-before-client-persist", outcome, 100, "commit-" + uuid.uuid4().hex)
    s = state(outcome)
    assert s["effect"] is not None, s
    assert s["refusal"] is None, s
    cleanup(outcome)


def scenario_3(rounds: int = 100) -> None:
    from dar_v36_14.postgres_authority import PostgresAuthority
    authority = PostgresAuthority(DSN)
    for _ in range(rounds):
        outcome = "race-" + uuid.uuid4().hex
        epoch = 100
        assert authority.fence(outcome, epoch)[0] == 200
        barrier = threading.Barrier(2)
        results = []

        def do_refuse():
            barrier.wait()
            results.append(("refuse", authority.refuse(outcome, epoch, "r-" + uuid.uuid4().hex)))

        def do_commit():
            barrier.wait()
            results.append(("commit", authority.commit(outcome, epoch, "c-" + uuid.uuid4().hex)))

        a = threading.Thread(target=do_refuse)
        b = threading.Thread(target=do_commit)
        a.start(); b.start(); a.join(); b.join()
        s = state(outcome)
        successful_commit = [r for kind, r in results if kind == "commit" and r[0] == 200 and not r[1].get("idempotent", False)]
        assert len(successful_commit) <= 1, results
        if s["effect"] is not None:
            assert len(successful_commit) == 1, (results, s)
        else:
            assert s["refusal"] is not None, (results, s)
        cleanup(outcome)


def scenario_4() -> None:
    outcome = "crash4-" + uuid.uuid4().hex
    refusal_id = "original-refusal-" + uuid.uuid4().hex
    kill_after_marker("refusal-before-client-persist", outcome, 100, refusal_id)
    s = state(outcome)
    assert s["refusal"] is not None, s
    from dar_v36_14.postgres_authority import PostgresAuthority
    authority = PostgresAuthority(DSN)
    status, body = authority.commit(outcome, 100, "new-key-after-crash")
    assert status == 409 and body["error"] == "terminal_refusal", (status, body)
    cleanup(outcome)


def scenario_5() -> None:
    outcome = "crash5-" + uuid.uuid4().hex
    kill_after_marker("torn-write", outcome, 100, "torn-refusal")
    s = state(outcome)
    assert s["refusal"] is None, s
    assert s["fence"] is None, s
    cleanup(outcome)


def main() -> None:
    from dar_v36_14.postgres_authority import PostgresAuthority
    PostgresAuthority(DSN)
    results = {}
    for name, fn in [
        ("crash_after_external_refusal_before_local_persistence", scenario_1),
        ("crash_after_external_commit_before_local_persistence", scenario_2),
        ("refusal_commit_race_100_runs", scenario_3),
        ("new_idempotency_key_after_crash_cannot_bypass_refusal", scenario_4),
        ("torn_transaction_write_rolls_back_after_SIGKILL", scenario_5),
    ]:
        fn()
        results[name] = "PASS"
        print(f"{name}: PASS")
    print(json.dumps({"evidence_type": "five-scenario-postgresql-crash-boundary", "tests": results, "verdict": "PASS"}, sort_keys=True))


if __name__ == "__main__" and not os.environ.get("CRASH_BOUNDARY_WORKER"):
    main()
