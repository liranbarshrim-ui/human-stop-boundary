"""A13 evidence against the real PostgreSQL authority."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dar_v36_14.postgres_authority import PostgresAuthority

DSN = os.environ["DATABASE_URL"]


def cleanup(authority: PostgresAuthority, prefix: str) -> None:
    with authority._connect() as conn:
        conn.execute("DELETE FROM dar_refusals WHERE outcome_key LIKE %s", (prefix + "%",))
        conn.execute("DELETE FROM dar_effects WHERE outcome_key LIKE %s", (prefix + "%",))
        conn.execute("DELETE FROM dar_fences WHERE outcome_key LIKE %s", (prefix + "%",))


def run() -> dict:
    authority = PostgresAuthority(DSN)
    prefix = "a13-" + uuid.uuid4().hex + "-"
    try:
        outcome = prefix + "same-epoch"
        assert authority.fence(outcome, 10)[0] == 200
        assert authority.refuse(outcome, 10, "r1")[0] == 200
        status, body = authority.commit(outcome, 10, "fresh-commit")
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)

        outcome = prefix + "higher-fence"
        assert authority.fence(outcome, 10)[0] == 200
        assert authority.refuse(outcome, 10, "r2")[0] == 200
        status, body = authority.fence(outcome, 11)
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)
        status, body = authority.commit(outcome, 11, "fresh-commit-11")
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)

        outcome = prefix + "retry"
        assert authority.fence(outcome, 20)[0] == 200
        status, body = authority.refuse(outcome, 20, "r3")
        assert status == 200 and body.get("idempotent") is False, (status, body)
        status, body = authority.refuse(outcome, 20, "r3")
        assert status == 200 and body.get("idempotent") is True, (status, body)
        status, body = authority.commit(outcome, 20, "fresh-commit-20")
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)

        outcome = prefix + "stale"
        assert authority.fence(outcome, 30)[0] == 200
        status, body = authority.refuse(outcome, 29, "stale-refusal")
        assert status == 409 and body["error"] == "fence_rollback", (status, body)
        status, body = authority.refuse(outcome, 30, "r5")
        assert status == 200, (status, body)
        status, body = authority.commit(outcome, 30, "fresh-commit-30")
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)

        return {
            "evidence_type": "a13-real-postgresql-terminal-refusal",
            "authority": "dar_v36_14.postgres_authority.PostgresAuthority",
            "database": "PostgreSQL",
            "checks": {
                "same_epoch_commit_rejected": "PASS",
                "higher_numeric_fence_cannot_clear_refusal": "PASS",
                "terminal_refusal_retry_is_idempotent": "PASS",
                "stale_refusal_rejected": "PASS",
            },
            "verdict": "PASS",
        }
    finally:
        cleanup(authority, prefix)


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
