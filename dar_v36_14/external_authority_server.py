"""External authority for DAR verification.

The external authority is deliberately fail-closed when PostgreSQL persistence
is requested but DATABASE_URL is absent or unusable. In-memory mode is only
allowed when persistence mode is explicitly ``memory`` (or omitted).
When DATABASE_URL is configured, all authoritative state is stored in
PostgreSQL and refusal/commit serialize through a transaction-scoped
advisory lock. This makes restart persistence testable without silently
falling back to memory. It is still deployment evidence, not production
certification.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


PERSISTENCE_MODE = os.environ.get("DAR_PERSISTENCE_MODE", "memory").strip().lower()
DB_URL = os.environ.get("DATABASE_URL", "").strip()

if PERSISTENCE_MODE not in {"memory", "postgres"}:
    raise RuntimeError(f"Unsupported DAR_PERSISTENCE_MODE: {PERSISTENCE_MODE!r}")
if PERSISTENCE_MODE == "postgres" and not DB_URL:
    raise RuntimeError("DAR_PERSISTENCE_MODE=postgres requires DATABASE_URL")

if DB_URL:
    try:
        from dar_v36_14.postgres_authority import PostgresAuthority
    except ModuleNotFoundError as exc:
        # Render executes this file directly, so its containing directory is
        # on sys.path while the repository root may not be. Keep the import
        # explicit and fail closed for any other missing dependency.
        if exc.name != "dar_v36_14":
            raise
        from postgres_authority import PostgresAuthority

    authority = PostgresAuthority(DB_URL)
else:
    authority = None

BOOT_ID = uuid.uuid4().hex
lock = threading.RLock()
fences: dict[str, int] = {}
refusals: dict[str, list[object]] = {}
effects: dict[str, dict[str, object]] = {}
committed_outcomes: dict[str, str] = {}


def response(handler: BaseHTTPRequestHandler, status: int, body: dict) -> None:
    raw = json.dumps(body, sort_keys=True).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        pass

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            if authority:
                try:
                    authority.health()
                except Exception as exc:
                    return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})
            return response(self, 200, {
                "ok": True,
                "persistence": "postgres" if authority else "memory",
                "boot_id": BOOT_ID,
            })
        if path == "/state":
            if authority:
                try:
                    body = authority.state()
                    body["boot_id"] = BOOT_ID
                    return response(self, 200, body)
                except Exception as exc:
                    return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})
            with lock:
                return response(self, 200, {
                    "fences": dict(fences),
                    "refusals": dict(refusals),
                    "effects": dict(effects),
                    "committed_outcomes": dict(committed_outcomes),
                    "boot_id": BOOT_ID,
                })
        if path == "/":
            return response(self, 200, {
                "service": "DAR external authority",
                "health": "/health",
                "state": "/state",
                "boot_id": BOOT_ID,
            })
        return response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")

        if authority:
            try:
                if path == "/fence":
                    status, body = authority.fence(data["outcome"], int(data["epoch"]))
                    return response(self, status, body)
                if path == "/refuse":
                    status, body = authority.refuse(data["outcome"], int(data["epoch"]), data["refusal_id"])
                    return response(self, status, body)
                if path == "/commit":
                    status, body = authority.commit(data["outcome"], int(data["epoch"]), data["idempotency_key"])
                    return response(self, status, body)
            except Exception as exc:
                return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})
            return response(self, 404, {"error": "not_found"})

        with lock:
            if path == "/fence":
                outcome = data["outcome"]
                epoch = int(data["epoch"])
                if epoch < fences.get(outcome, 0):
                    return response(self, 409, {"ok": False, "error": "fence_rollback"})
                if outcome in refusals:
                    return response(self, 409, {"ok": False, "error": "terminal_refusal"})
                fences[outcome] = epoch
                return response(self, 200, {"ok": True})

            if path == "/refuse":
                outcome = data["outcome"]
                epoch = int(data["epoch"])
                refusal_id = data["refusal_id"]
                existing = refusals.get(outcome)
                if existing is not None:
                    same = existing == [epoch, refusal_id]
                    return response(self, 200, {"ok": same, "idempotent": same})
                if epoch < fences.get(outcome, 0):
                    return response(self, 409, {"ok": False, "error": "fence_rollback"})
                fences[outcome] = epoch
                refusals[outcome] = [epoch, refusal_id]
                return response(self, 200, {"ok": True, "idempotent": False})

            if path == "/commit":
                outcome = data["outcome"]
                epoch = int(data["epoch"])
                idem = data["idempotency_key"]
                if outcome in refusals:
                    return response(self, 409, {"ok": False, "error": "terminal_refusal"})
                if fences.get(outcome, 0) != epoch:
                    return response(self, 409, {"ok": False, "error": "stale_fence"})
                if idem in effects:
                    return response(self, 200, {"ok": True, "idempotent": True})
                if outcome in committed_outcomes:
                    return response(self, 409, {"ok": False, "error": "outcome_already_committed"})
                effects[idem] = {"outcome": outcome, "epoch": epoch}
                committed_outcomes[outcome] = idem
                return response(self, 200, {"ok": True, "idempotent": False})

        return response(self, 404, {"error": "not_found"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
