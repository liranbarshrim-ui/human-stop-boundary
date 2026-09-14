"""External authority for DAR verification.

Default mode remains in-memory for deterministic local/deployment tests.
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# PostgreSQL mode is fail-closed: a configured but unusable database must not
# silently downgrade the authority boundary to ephemeral memory.
DB_URL = os.environ.get("DATABASE_URL", "").strip()
if DB_URL:
    from dar_v36_14.postgres_authority import PostgresAuthority

    authority = PostgresAuthority(DB_URL)
else:
    authority = None

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
        if self.path == "/health":
            if authority:
                try:
                    authority.health()
                except Exception as exc:
                    return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})
            return response(self, 200, {"ok": True, "persistence": "postgres" if authority else "memory"})
        if self.path == "/state":
            if authority:
                try:
                    return response(self, 200, authority.state())
                except Exception as exc:
                    return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})
            with lock:
                return response(self, 200, {
                    "fences": dict(fences),
                    "refusals": dict(refusals),
                    "effects": dict(effects),
                    "committed_outcomes": dict(committed_outcomes),
                })
        return response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")

        if authority:
            try:
                if self.path == "/fence":
                    status, body = authority.fence(data["outcome"], int(data["epoch"]))
                    return response(self, status, body)
                if self.path == "/refuse":
                    status, body = authority.refuse(data["outcome"], int(data["epoch"]), data["refusal_id"])
                    return response(self, status, body)
                if self.path == "/commit":
                    status, body = authority.commit(data["outcome"], int(data["epoch"]), data["idempotency_key"])
                    return response(self, status, body)
            except Exception as exc:
                return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})
            return response(self, 404, {"error": "not_found"})

        with lock:
            if self.path == "/fence":
                outcome = data["outcome"]
                epoch = int(data["epoch"])
                if epoch < fences.get(outcome, 0):
                    return response(self, 409, {"ok": False, "error": "fence_rollback"})
                if outcome in refusals:
                    return response(self, 409, {"ok": False, "error": "terminal_refusal"})
                fences[outcome] = epoch
                return response(self, 200, {"ok": True})

            if self.path == "/refuse":
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

            if self.path == "/commit":
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
