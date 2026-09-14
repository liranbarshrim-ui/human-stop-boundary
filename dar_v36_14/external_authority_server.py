"""Minimal external authority for deployment-level DAR verification.

This service is deliberately separate from the DAR client. The same lock
serializes terminal refusal and protected commit for each outcome_key.
It is suitable for deployment testing, not production certification.
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

lock = threading.RLock()
fences: dict[str, int] = {}
refusals: dict[str, list[object]] = {}
effects: dict[str, dict[str, object]] = {}


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
            return response(self, 200, {"ok": True})
        if self.path == "/state":
            with lock:
                return response(self, 200, {
                    "fences": dict(fences),
                    "refusals": dict(refusals),
                    "effects": dict(effects),
                })
        return response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")
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
                effects[idem] = {"outcome": outcome, "epoch": epoch}
                return response(self, 200, {"ok": True, "idempotent": False})

        return response(self, 404, {"error": "not_found"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
