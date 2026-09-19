#!/usr/bin/env python3
"""Optional local A/B helper for the reference staging integration.

Not required to verify the Git commit. See README.md.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(Path(__file__).resolve().parent)]

from dar_v36_14.dar.effect_gate import EffectGate, EffectRequest
from dar_v36_14.dar.kernel import Kernel
from dar_v36_14.dar.model import SystemState
from dar_v36_14.dar.store import Snapshot, Store
from identity import DeploymentRequest
from staging_adapter import StagingDeploymentAdapter

SECRET = b"reference-integration-secret-32b!!"
AUTH = "reference-staging-auth-secret"
PORT = int(os.environ.get("STAGING_PORT", "19090"))
BASE = f"http://127.0.0.1:{PORT}"


class Journal:
    def __init__(self) -> None:
        self.rows: list = []
    def append(self, row) -> None:
        self.rows.append(dict(row))
    def _validated_state(self):
        return {r["key"]: dict(r) for r in self.rows}


def http_json(method: str, path: str, body=None):
    import urllib.request
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        if hasattr(e, "read"):
            try:
                return e.code, json.loads(e.read().decode())
            except Exception:
                return getattr(e, "code", 0), {"error": str(e)}
        return 0, {"error": str(e)}


def start_staging():
    data = Path(tempfile.mkdtemp())
    script = Path(__file__).resolve().parent / "staging_server.py"
    proc = subprocess.Popen([sys.executable, str(script), "--host", "127.0.0.1", "--port", str(PORT), "--data-dir", str(data), "--secret", AUTH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        st, _ = http_json("GET", "/health")
        if st == 200:
            return proc
        time.sleep(0.05)
    raise RuntimeError("staging failed to start")


def make_kernel(store_path: Path):
    store = Store(store_path, SECRET)
    state0 = SystemState(0, {"human": {"root": frozenset({"WRITE", "READ"})}}, {})
    store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), state0.canonical(), "REFBOOT"))
    kernel = Kernel(store, SECRET, boot_id="REFBOOT")
    return store, kernel, EffectGate(kernel)


def main() -> int:
    proc = start_staging()
    try:
        http_json("POST", "/staging/reset", {})
        adapter = StagingDeploymentAdapter(BASE, AUTH)
        with tempfile.TemporaryDirectory() as td:
            store, kernel, gate = make_kernel(Path(td) / "state")
            art = b"reference-artifact"
            req = DeploymentRequest(art, "local-staging", "qualify-A")
            params = {"deployment_id": req.deployment_id, "artifact_digest": req.artifact_digest, "staging_target": req.staging_target, "label": req.label, "artifact_b64": base64.b64encode(art).decode()}
            s = store._read()
            cap = kernel.issue_protected("human", "root", "WRITE", SystemState(s.epoch + 1, {"human": {"root": frozenset({"WRITE", "READ"})}}, {}), nonce="na", params=params, effect_id=req.effect_id, outcome_key=req.outcome_key)
            adapter.fences[req.outcome_key] = store._read().epoch
            gate.execute_protected(EffectRequest(cap, "human", "root", "WRITE", req.effect_id, "WRITE", req.outcome_key), adapter, params, Journal())
            obs = adapter.observe_staging(req.deployment_id)
            print("A", obs.get("state"), obs.get("artifact_digest") == req.artifact_digest)
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
