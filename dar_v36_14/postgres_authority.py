"""Durable PostgreSQL state for the external DAR authority.

The database is the authority boundary: refusal and protected commit for the
same outcome serialize under one PostgreSQL transaction and advisory lock.
The module fails closed when DATABASE_URL is configured but unusable.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row


class PostgresAuthority:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.environ.get("DATABASE_URL", "")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL authority")
        self._init_schema()

    def _connect(self):
        return psycopg.connect(
            self.dsn,
            row_factory=dict_row,
            connect_timeout=10,
            sslmode=os.environ.get("DAR_DB_SSLMODE", "require").strip().lower() or "require",
        )

    @staticmethod
    def _lock_key(outcome: str) -> int:
        value = int.from_bytes(hashlib.sha256(outcome.encode("ascii")).digest()[:8], "big")
        return value - (1 << 64) if value >= (1 << 63) else value

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dar_fences (
                    outcome_key TEXT PRIMARY KEY,
                    fence BIGINT NOT NULL CHECK (fence >= 0)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dar_refusals (
                    outcome_key TEXT PRIMARY KEY,
                    epoch BIGINT NOT NULL CHECK (epoch >= 0),
                    refusal_id TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dar_effects (
                    idempotency_key TEXT PRIMARY KEY,
                    outcome_key TEXT NOT NULL UNIQUE,
                    epoch BIGINT NOT NULL CHECK (epoch >= 0)
                )
            """)

    def _lock(self, conn, outcome: str) -> None:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (self._lock_key(outcome),))

    def health(self) -> bool:
        with self._connect() as conn:
            conn.execute("SELECT 1")
        return True

    def state(self) -> dict[str, Any]:
        with self._connect() as conn:
            fences = {r["outcome_key"]: r["fence"] for r in conn.execute("SELECT * FROM dar_fences")}
            refusals = {r["outcome_key"]: [r["epoch"], r["refusal_id"]] for r in conn.execute("SELECT * FROM dar_refusals")}
            effects = {r["idempotency_key"]: {"outcome": r["outcome_key"], "epoch": r["epoch"]} for r in conn.execute("SELECT * FROM dar_effects")}
            committed = {r["outcome_key"]: r["idempotency_key"] for r in conn.execute("SELECT outcome_key, idempotency_key FROM dar_effects")}
            return {"fences": fences, "refusals": refusals, "effects": effects, "committed_outcomes": committed}

    def fence(self, outcome: str, epoch: int) -> tuple[int, dict[str, Any]]:
        with self._connect() as conn:
            self._lock(conn, outcome)
            row = conn.execute("SELECT fence FROM dar_fences WHERE outcome_key=%s", (outcome,)).fetchone()
            current = int(row["fence"]) if row else 0
            if epoch < current:
                return 409, {"ok": False, "error": "fence_rollback"}
            if conn.execute("SELECT 1 FROM dar_refusals WHERE outcome_key=%s", (outcome,)).fetchone():
                return 409, {"ok": False, "error": "terminal_refusal"}
            conn.execute("INSERT INTO dar_fences(outcome_key, fence) VALUES (%s,%s) ON CONFLICT (outcome_key) DO UPDATE SET fence=EXCLUDED.fence", (outcome, epoch))
            return 200, {"ok": True}

    def refuse(self, outcome: str, epoch: int, refusal_id: str) -> tuple[int, dict[str, Any]]:
        with self._connect() as conn:
            self._lock(conn, outcome)
            existing = conn.execute("SELECT epoch, refusal_id FROM dar_refusals WHERE outcome_key=%s", (outcome,)).fetchone()
            if existing:
                same = int(existing["epoch"]) == epoch and existing["refusal_id"] == refusal_id
                return 200, {"ok": same, "idempotent": same}
            fence = conn.execute("SELECT fence FROM dar_fences WHERE outcome_key=%s", (outcome,)).fetchone()
            current = int(fence["fence"]) if fence else 0
            if epoch < current:
                return 409, {"ok": False, "error": "fence_rollback"}
            if conn.execute("SELECT 1 FROM dar_effects WHERE outcome_key=%s", (outcome,)).fetchone():
                return 409, {"ok": False, "error": "outcome_already_committed", "late": True}
            conn.execute("INSERT INTO dar_fences(outcome_key, epoch) VALUES (%s,%s) ON CONFLICT (outcome_key) DO UPDATE SET fence=GREATEST(dar_fences.fence, EXCLUDED.fence)", (outcome, epoch))
            conn.execute("INSERT INTO dar_refusals(outcome_key, epoch, refusal_id) VALUES (%s,%s,%s)", (outcome, epoch, refusal_id))
            return 200, {"ok": True, "idempotent": False}

    def commit(self, outcome: str, epoch: int, idem: str) -> tuple[int, dict[str, Any]]:
        with self._connect() as conn:
            self._lock(conn, outcome)
            if conn.execute("SELECT 1 FROM dar_refusals WHERE outcome_key=%s", (outcome,)).fetchone():
                return 409, {"ok": False, "error": "terminal_refusal"}
            fence = conn.execute("SELECT fence FROM dar_fences WHERE outcome_key=%s", (outcome,)).fetchone()
            current = int(fence["fence"]) if fence else 0
            if current != epoch:
                return 409, {"ok": False, "error": "stale_fence"}
            existing = conn.execute("SELECT outcome_key FROM dar_effects WHERE idempotency_key=%s", (idem,)).fetchone()
            if existing:
                if existing["outcome_key"] == outcome:
                    return 200, {"ok": True, "idempotent": True}
                return 409, {"ok": False, "error": "idempotency_key_reuse"}
            if conn.execute("SELECT 1 FROM dar_effects WHERE outcome_key=%s", (outcome,)).fetchone():
                return 409, {"ok": False, "error": "outcome_already_committed"}
            conn.execute("INSERT INTO dar_effects(idempotency_key, outcome_key, epoch) VALUES (%s,%s,%s)", (idem, outcome, epoch))
            return 200, {"ok": True, "idempotent": False}
