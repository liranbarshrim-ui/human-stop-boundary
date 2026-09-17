"""A13 evidence against the real PostgreSQL authority.

A13 requires terminal refusal to be durable, authoritative, and impossible to
clear or bypass by a numeric fence update. This test exercises the production
PostgresAuthority implementation, not the in-memory/reference model.
"""
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
    outcomes = {
        "refusal_blocks_same_epoch_commit": prefix + "same-epoch",
        "refusal_survives_higher_numeric_fence_attempt": prefix + "higher-fence",
        "refusal_is_idempotent": prefix + "retry",
        "refusal_wins_against_stale_epoch": prefix + "stale",
    }
    try:
        # Terminal refusal is published at epoch 10.
        outcome = outcomes["refusal_blocks_same_epoch_commit"]
        assert authority.fence(outcome, 10)[0] == 200
        assert authority.refuse(outcome, 10, "r1")[0] == 200
        status, body = authority.commit(outcome, 10, "fresh-commit")
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)

        # A numeric fence update cannot clear terminal refusal, even at a higher epoch.
        outcome = outcomes["refusal_survives_higher_numeric_fence_attempt"]
        assert authority.fence(outcome, 10)[0] == 200
        assert authority.refuse(outcome, 10, "r2")[0] == 200
        status, body = authority.fence(outcome, 11)
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)
        status, body = authority.commit(outcome, 11, "fresh-commit-11")
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)

        # Exact retry is idempotent; a different refusal cannot replace the terminal marker.
        outcome = outcomes["refusal_is_idempotent"]
        assert authority.fence(outcome, 20)[0] == 200
        status, body = authority.refuse(outcome, 20, "r3")
        assert status == 200 and body.get("idempotent") is False, (status, body)
        status, body = authority.refuse(outcome, 20, "r3")
        assert status == 200 and body.get("idempotent") is True, (status, body)
        status, body = authority.refuse(outcome, 21, "r4")
        assert status == 200 and body.get("ok") is False and body.get("idempotent") is False, (status, body)
        status, body = authority.commit(outcome, 20, "fresh-commit-20")
        assert status == 409 and body["error"] == "terminal_refusal", (status, body)

        # A stale refusal cannot overwrite a newer fence, and the terminal refusal still blocks commit.
        outcome = outcomes["refusal_wins_against_stale_epoch"]
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
