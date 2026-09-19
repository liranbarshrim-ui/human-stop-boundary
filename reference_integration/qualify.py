#!/usr/bin/env python3
"""Runtime A/B qualification and adversarial checks for the staging reference integration."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(Path(__file__).resolve().parent)]

from dar_v36_14.dar.effect_gate import EffectGate, EffectRequest
from dar_v36_14.dar.kernel import Kernel
from dar_v36_14.dar.model import SystemState
from dar_v36_14.dar.refusal import RefusalAuthority
from dar_v36_14.dar.store import Snapshot, Store
from identity import DeploymentRequest
from staging_adapter import StagingDeploymentAdapter

SECRET = b"reference-integration-secret-32b!!"
AUTH = os.environ.get("STAGING_AUTH_SECRET", "ci-reference-staging-secret-32b!!")
PORT = int(os.environ.get("STAGING_PORT", "19090"))
BASE = f"http://127.0.0.1:{PORT}"


class Journal:
    def __init__(self): self.rows = []
    def append(self, row): self.rows.append(dict(row))
    def _validated_state(self): return {r["key"]: dict(r) for r in self.rows}


def http_json(method, path, body=None):
    import urllib.request
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        raw = e.read().decode() if hasattr(e, "read") else str(e)
        try: return e.code, json.loads(raw)
        except Exception: return getattr(e, "code", 0), {"error": raw}


def start_staging():
    data = Path(tempfile.mkdtemp())
    script = Path(__file__).resolve().parent / "staging_server.py"
    proc = subprocess.Popen([sys.executable, str(script), "--host", "127.0.0.1", "--port", str(PORT), "--data-dir", str(data), "--secret", AUTH], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(100):
        st, _ = http_json("GET", "/health")
        if st == 200: return proc
        time.sleep(0.05)
    out = proc.stdout.read() if proc.stdout else ""
    raise RuntimeError(f"staging failed to start: {out}")


def admin_mac(deployment_id, reason):
    canonical = f"RESET|{deployment_id}|{reason}".encode()
    return hmac.new(AUTH.encode(), canonical, hashlib.sha256).hexdigest()


def reset():
    return http_json("POST", "/staging/reset", {"deployment_id": "qualify", "reason": "qualification", "mac": admin_mac("qualify", "qualification")})


def make_kernel(store_path):
    store = Store(store_path, SECRET)
    state0 = SystemState(0, {"human": {"root": frozenset({"WRITE", "READ"})}}, {})
    store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), state0.canonical(), "REFBOOT"))
    return store, Kernel(store, SECRET, boot_id="REFBOOT")


def prepare(store, kernel, req, params):
    s = store._read()
    cap = kernel.issue_protected("human", "root", "WRITE", SystemState(s.epoch + 1, {"human": {"root": frozenset({"WRITE", "READ"})}}, {}), nonce=uuid.uuid4().hex, params=params, effect_id=req.effect_id, outcome_key=req.outcome_key)
    return cap, store._read().epoch


def run():
    proc = start_staging()
    evidence = []
    try:
        st, body = reset(); assert st == 200 and body.get("ok"), (st, body)

        art = b"reference-artifact-v2"
        req = DeploymentRequest(art, "ci-staging", "qualification")
        params = {"deployment_id": req.deployment_id, "artifact_digest": req.artifact_digest, "staging_target": req.staging_target, "label": req.label, "artifact_b64": base64.b64encode(art).decode()}

        # A: valid protected authorization produces the observable staging effect.
        with tempfile.TemporaryDirectory() as td:
            store, kernel = make_kernel(Path(td) / "state")
            gate = EffectGate(kernel); adapter = StagingDeploymentAdapter(BASE, AUTH)
            cap, epoch = prepare(store, kernel, req, params); adapter.fences[req.outcome_key] = epoch
            gate.execute_protected(EffectRequest(cap, "human", "root", "WRITE", req.effect_id, "WRITE", req.outcome_key), adapter, params, Journal())
            obs = adapter.observe_staging(req.deployment_id)
            assert obs.get("state") == "DEPLOYED" and obs.get("artifact_digest") == req.artifact_digest, obs
            evidence.append({"test":"A_normal","result":"PASS","state":obs.get("state")})

        # B: valid terminal refusal prevents the observable effect.
        req_b = DeploymentRequest(b"refused-artifact-v2", "ci-staging", "qualification-B")
        params_b = {"deployment_id": req_b.deployment_id, "artifact_digest": req_b.artifact_digest, "staging_target": req_b.staging_target, "label": req_b.label, "artifact_b64": base64.b64encode(req_b.artifact_bytes).decode()}
        with tempfile.TemporaryDirectory() as td:
            store, kernel = make_kernel(Path(td) / "state")
            gate = EffectGate(kernel); adapter = StagingDeploymentAdapter(BASE, AUTH)
            cap, epoch = prepare(store, kernel, req_b, params_b); adapter.fences[req_b.outcome_key] = epoch
            auth = RefusalAuthority(store, {"human": SECRET})
            refusal = auth.issue_protected("human", req_b.effect_id, cap.txid, req_b.outcome_key, target_epoch=epoch + 1)
            auth.commit_protected(refusal, adapter)
            try:
                gate.execute_protected(EffectRequest(cap, "human", "root", "WRITE", req_b.effect_id, "WRITE", req_b.outcome_key), adapter, params_b, Journal())
                raise AssertionError("protected execution unexpectedly succeeded after refusal")
            except Exception:
                pass
            obs = adapter.observe_staging(req_b.deployment_id)
            assert obs.get("state") != "DEPLOYED", obs
            evidence.append({"test":"B_refusal","result":"PASS","state":obs.get("state")})

            # V8: wipe only local adapter state; staging must retain terminal refusal.
            adapter.refusals.clear(); adapter.fences.clear()
            idem = "replay-" + uuid.uuid4().hex
            try:
                adapter.commit(idem, req_b.outcome_key, epoch, params_b)
                raise AssertionError("replay unexpectedly deployed after local refusal wipe")
            except Exception:
                pass
            obs2 = adapter.observe_staging(req_b.deployment_id)
            assert obs2.get("state") != "DEPLOYED", obs2
            evidence.append({"test":"V8_local_state_wipe_replay","result":"PASS","state":obs2.get("state")})

        # V4/V7: direct unauthenticated deployment and bad token must not create the effect.
        st, _ = http_json("POST", "/staging/deploy", {"deployment_id":"attacker-deploy","artifact_digest":hashlib.sha256(b"x").hexdigest(),"artifact_b64":base64.b64encode(b"x").decode()})
        assert st == 401, st
        evidence.append({"test":"V4_V7_unauth_deploy","result":"PASS","http":st})

        st, _ = http_json("POST", "/staging/reset", {})
        assert st == 401, st
        evidence.append({"test":"reset_without_mac","result":"PASS","http":st})

        print(json.dumps({"status":"PASS","evidence":evidence}, sort_keys=True))
        return 0
    finally:
        proc.terminate()
        try: proc.wait(timeout=2)
        except Exception: proc.kill()


if __name__ == "__main__":
    raise SystemExit(run())
