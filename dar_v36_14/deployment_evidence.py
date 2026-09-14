"""Deployment evidence: DAR client against an independently spawned HTTP authority.

The authority is a separate OS process. The DAR client communicates with it
only over HTTP; no in-process object or shared Python state is used for the
protected decision. This is deployment-level evidence, not production
certification or evidence about an unrelated third-party system.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

from dar import Snapshot, Store
from dar.canonical import canonical_digest
from dar.effect_transaction import AdapterContractError, EffectTxn, FencedEffectAdapter, TxnStatus, protected_commit
from dar.refusal import RefusalAuthority

OUTCOME = "cafebabe"
EPOCH = 7


def post(base, path, body):
    req = Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def get(base):
    with urlopen(base + "/state", timeout=5) as r:
        return json.loads(r.read())


class HTTPFencedAdapter(FencedEffectAdapter):
    """DAR adapter backed only by the independent authority process."""
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


def launch_authority():
    authority = r'''
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUTCOME = "cafebabe"
EPOCH = 7
lock = threading.RLock()
fences = {OUTCOME: EPOCH}
refusals = {}
effects = {}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def reply(self, status, body):
        raw = json.dumps(body, sort_keys=True).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/state":
            with lock: return self.reply(200, {"fences": dict(fences), "refusals": dict(refusals), "effects": dict(effects)})
        return self.reply(404, {"error":"not_found"})
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0")); d = json.loads(self.rfile.read(n) or b"{}")
        with lock:
            if self.path == "/refuse":
                o, e, rid = d["outcome"], int(d["epoch"]), d["refusal_id"]
                existing = refusals.get(o)
                if existing:
                    return self.reply(200, {"ok": existing == [e, rid], "idempotent": existing == [e, rid]})
                if e < fences.get(o, 0): return self.reply(200, {"ok":False,"error":"fence_rollback"})
                fences[o] = e; refusals[o] = [e, rid]
                return self.reply(200, {"ok":True,"idempotent":False})
            if self.path == "/commit":
                o, e, idem = d["outcome"], int(d["epoch"]), d["idempotency_key"]
                if o in refusals: return self.reply(200, {"ok":False,"error":"terminal_refusal"})
                if fences.get(o, 0) != e: return self.reply(200, {"ok":False,"error":"stale_fence"})
                if idem in effects: return self.reply(200, {"ok":True,"idempotent":True})
                effects[idem] = {"outcome":o,"epoch":e}; return self.reply(200, {"ok":True,"idempotent":False})
        return self.reply(404, {"error":"not_found"})

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
print(server.server_address[1], flush=True)
server.serve_forever()
'''
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    p = subprocess.Popen([sys.executable, "-c", authority], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    port = int(p.stdout.readline().strip())
    return p, f"http://127.0.0.1:{port}"


def make_store(root):
    store = Store(Path(root) / "state", b"x" * 32)
    store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), {"epoch": 0, "permissions": {}, "governance": {}}, "B", tuple(), tuple()))
    return store


def main():
    authority, base = launch_authority()
    evidence = {
        "deployment": "independent OS process + HTTP boundary",
        "authority_pid": authority.pid,
        "authority_endpoint": base,
        "outcome_key": OUTCOME,
        "target_epoch": EPOCH,
    }
    try:
        # Prove the endpoint is actually reachable before DAR touches it.
        evidence["initial_external_state"] = get(base)
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
                evidence["simulated_local_crash"] = str(exc)
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

        evidence["final_external_state"] = get(base)
        evidence["verdict"] = "PASS"
    finally:
        authority.terminate()
        try:
            authority.wait(timeout=2)
        except subprocess.TimeoutExpired:
            authority.kill(); authority.wait(timeout=2)
    print(json.dumps(evidence, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
