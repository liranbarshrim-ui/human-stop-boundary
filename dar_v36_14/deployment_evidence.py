"""Deployment-level evidence harness for the DAR protected-outcome contract.

This is deliberately a separate HTTP authority process. DAR is the client;
the authority owns the outcome state, terminal refusal marker, fence and
commit atomically under one lock. The harness records externally observed
HTTP results so the evidence is not a unit-test-only claim.
"""
from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

OUTCOME = "deadbeef"
EPOCH = 7


class Authority:
    def __init__(self):
        self.lock = threading.RLock()
        self.fence = {OUTCOME: EPOCH}
        self.refusal = {}
        self.effects = {}

    def refuse(self, outcome, epoch, refusal_id):
        with self.lock:
            if outcome in self.refusal:
                if self.refusal[outcome] == (epoch, refusal_id):
                    return {"ok": True, "idempotent": True}
                return {"ok": False, "error": "conflicting_terminal_refusal"}
            if epoch < self.fence.get(outcome, 0):
                return {"ok": False, "error": "fence_rollback"}
            self.fence[outcome] = epoch
            self.refusal[outcome] = (epoch, refusal_id)
            return {"ok": True, "idempotent": False}

    def commit(self, outcome, epoch, idem):
        with self.lock:
            if outcome in self.refusal:
                return {"ok": False, "error": "terminal_refusal"}
            if self.fence.get(outcome, 0) != epoch:
                return {"ok": False, "error": "stale_fence"}
            if idem in self.effects:
                return {"ok": True, "idempotent": True}
            self.effects[idem] = {"outcome": outcome, "epoch": epoch}
            return {"ok": True, "idempotent": False}

    def state(self):
        with self.lock:
            return {
                "fence": self.fence.get(OUTCOME, 0),
                "terminal_refusal": OUTCOME in self.refusal,
                "effects": dict(self.effects),
            }


AUTHORITY = Authority()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _json(self, status, body):
        raw = json.dumps(body, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/state":
            return self._json(200, AUTHORITY.state())
        self._json(404, {"error": "not_found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/refuse":
            return self._json(200, AUTHORITY.refuse(data["outcome"], int(data["epoch"]), data["refusal_id"]))
        if self.path == "/commit":
            return self._json(200, AUTHORITY.commit(data["outcome"], int(data["epoch"]), data["idempotency_key"]))
        self._json(404, {"error": "not_found"})


def post(base, path, body):
    req = Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def get(base, path):
    with urlopen(base + path, timeout=5) as r:
        return json.loads(r.read())


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    evidence = {
        "harness": "DAR deployment-level external-authority evidence",
        "authority": "separate HTTP process",
        "outcome": OUTCOME,
        "epoch": EPOCH,
    }
    try:
        before = post(base, "/commit", {"outcome": OUTCOME, "epoch": EPOCH, "idempotency_key": "before-refusal"})
        evidence["commit_before_refusal"] = before
        if not before["ok"]:
            raise AssertionError(before)

        # A distinct outcome is used for the refusal test so the successful
        # pre-refusal commit above cannot be retroactively converted to NO.
        test_outcome = "cafebabe"
        AUTHORITY.fence[test_outcome] = EPOCH
        refused = post(base, "/refuse", {"outcome": test_outcome, "epoch": EPOCH, "refusal_id": "r-1"})
        evidence["terminal_refusal"] = refused
        blocked = post(base, "/commit", {"outcome": test_outcome, "epoch": EPOCH, "idempotency_key": "after-refusal-new-id"})
        evidence["commit_after_terminal_refusal"] = blocked
        retry = post(base, "/refuse", {"outcome": test_outcome, "epoch": EPOCH, "refusal_id": "r-1"})
        evidence["refusal_retry"] = retry
        state = get(base, "/state")
        evidence["final_state"] = state

        assert blocked == {"ok": False, "error": "terminal_refusal"}, blocked
        assert retry == {"ok": True, "idempotent": True}, retry
        assert state["terminal_refusal"] is False  # primary OUTCOME was committed, not refused
        assert "after-refusal-new-id" not in state["effects"]
        evidence["verdict"] = "PASS"
    finally:
        server.shutdown()
        thread.join(timeout=2)

    print(json.dumps(evidence, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
