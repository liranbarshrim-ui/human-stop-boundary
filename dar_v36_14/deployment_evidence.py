"""Real deployment evidence: DAR client against a separate HTTP authority process."""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from dar import Snapshot, Store
from dar.canonical import canonical_digest
from dar.effect_transaction import AdapterContractError, EffectTxn, FencedEffectAdapter, TxnStatus, protected_commit
from dar.refusal import RefusalAuthority

OUTCOME = "cafebabe"
EPOCH = 7


class ExternalAuthority:
    """The deployed process: outcome fence/refusal/commit share one lock."""
    def __init__(self):
        self.lock = threading.RLock()
        self.fences = {}
        self.refusals = {}
        self.effects = {}

    def state(self):
        with self.lock:
            return {"fences": dict(self.fences), "refusals": dict(self.refusals), "effects": dict(self.effects)}

    def refuse(self, outcome, epoch, refusal_id):
        with self.lock:
            existing = self.refusals.get(outcome)
            if existing:
                return {"ok": existing == [epoch, refusal_id], "idempotent": existing == [epoch, refusal_id]}
            if epoch < self.fences.get(outcome, 0):
                return {"ok": False, "error": "fence_rollback"}
            self.fences[outcome] = epoch
            self.refusals[outcome] = [epoch, refusal_id]
            return {"ok": True, "idempotent": False}

    def commit(self, outcome, epoch, idem):
        with self.lock:
            if outcome in self.refusals:
                return {"ok": False, "error": "terminal_refusal"}
            if self.fences.get(outcome, 0) != epoch:
                return {"ok": False, "error": "stale_fence"}
            if idem in self.effects:
                return {"ok": True, "idempotent": True}
            self.effects[idem] = {"outcome": outcome, "epoch": epoch}
            return {"ok": True, "idempotent": False}


AUTHORITY = ExternalAuthority()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _reply(self, status, body):
        raw = json.dumps(body, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/state":
            return self._reply(200, AUTHORITY.state())
        return self._reply(404, {"error": "not_found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/fence":
            with AUTHORITY.lock:
                AUTHORITY.fences[data["outcome"]] = int(data["epoch"])
            return self._reply(200, {"ok": True})
        if self.path == "/refuse":
            return self._reply(200, AUTHORITY.refuse(data["outcome"], int(data["epoch"]), data["refusal_id"]))
        if self.path == "/commit":
            return self._reply(200, AUTHORITY.commit(data["outcome"], int(data["epoch"]), data["idempotency_key"]))
        return self._reply(404, {"error": "not_found"})


def post(base, path, body):
    req = Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def get(base):
    with urlopen(base + "/state", timeout=5) as r:
        return json.loads(r.read())


class HTTPFencedAdapter(FencedEffectAdapter):
    """DAR's external adapter contract backed only by the deployed HTTP process."""
    def __init__(self, base):
        self.base = base

    def current_fence(self, outcome_key):
        return get(self.base)["fences"].get(outcome_key, 0)

    def is_refused(self, outcome_key):
        return outcome_key in get(self.base)["refusals"]

    def refuse_outcome(self, outcome_key, fence_epoch, refusal_id):
        result = post(self.base, "/refuse", {"outcome": outcome_key, "epoch": fence_epoch, "refusal_id": refusal_id})
        if not result["ok"]:
            raise RuntimeError(result["error"])

    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        result = post(self.base, "/commit", {"outcome": outcome_key, "epoch": fence_epoch, "idempotency_key": idempotency_key})
        if not result["ok"]:
            raise RuntimeError(result["error"])
        return TxnStatus.COMMITTED

    def status(self, idempotency_key):
        return TxnStatus.COMMITTED if idempotency_key in get(self.base)["effects"] else TxnStatus.UNKNOWN

    def execute(self, idempotency_key, params):
        raise AssertionError("protected path must never call execute()")


def make_store(root):
    store = Store(Path(root) / "state", b"x" * 32)
    store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), {"epoch": 0, "permissions": {}, "governance": {}}, "B", tuple(), tuple()))
    return store


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    evidence = {"deployment": "separate HTTP authority process", "outcome_key": OUTCOME, "target_epoch": EPOCH}
    try:
        post(base, "/fence", {"outcome": OUTCOME, "epoch": EPOCH})
        adapter = HTTPFencedAdapter(base)
        with tempfile.TemporaryDirectory() as d:
            auth = RefusalAuthority(make_store(d), {"human-a": b"a" * 32})
            refusal = auth.issue_protected("human-a", "effect-1", "tx-1", OUTCOME, target_epoch=EPOCH, refusal_id="deploy-r1")

            real_write = auth.store._write_atomic
            def crash_after_external_refusal(snapshot):
                if snapshot.state_payload.get("refusals"):
                    raise RuntimeError("simulated crash after external terminal refusal")
                return real_write(snapshot)
            auth.store._write_atomic = crash_after_external_refusal
            try:
                auth.commit_protected(refusal, adapter)
            except RuntimeError as exc:
                evidence["simulated_crash"] = str(exc)
            else:
                raise AssertionError("crash simulation did not fire")

            external_after_crash = get(base)
            evidence["external_after_crash"] = external_after_crash
            assert OUTCOME in external_after_crash["refusals"]
            assert not external_after_crash["effects"]

            txn = EffectTxn("new-effect", "new-effect", "WRITE", canonical_digest({"x": 1}), OUTCOME, EPOCH)
            try:
                protected_commit(adapter, txn, {"x": 1})
            except AdapterContractError as exc:
                evidence["new_effect_denied"] = str(exc)
            else:
                raise AssertionError("new effect bypassed terminal refusal")

            retry = post(base, "/refuse", {"outcome": OUTCOME, "epoch": EPOCH, "refusal_id": "deploy-r1"})
            evidence["external_refusal_retry"] = retry
            assert retry == {"ok": True, "idempotent": True}

        evidence["verdict"] = "PASS"
    finally:
        server.shutdown()
        thread.join(timeout=2)
    print(json.dumps(evidence, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
