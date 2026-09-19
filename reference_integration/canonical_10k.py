#!/usr/bin/env python3
"""10K canonical runtime qualification for the isolated staging reference effect.

Runs repeated normal/refusal/replay transitions against one isolated staging
service. Any protected outcome observed after a valid refusal is a failure.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, subprocess, sys, tempfile, time, uuid
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
AUTH = os.environ.get("STAGING_DEPLOY_SECRET") or os.urandom(32).hex()
ADMIN = os.environ.get("STAGING_ADMIN_SECRET") or os.urandom(32).hex()
PORT = int(os.environ.get("STAGING_PORT", "19190"))
BASE = f"http://127.0.0.1:{PORT}"
N = int(os.environ.get("CANONICAL_10K", "10000"))


def http_json(method, path, body=None):
    import urllib.request
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        raw = e.read().decode() if hasattr(e, "read") else str(e)
        try:
            return e.code, json.loads(raw)
        except Exception:
            return getattr(e, "code", 0), {"error": raw}


def start_staging(data_dir):
    script = Path(__file__).resolve().parent / "staging_server.py"
    proc = subprocess.Popen([
        sys.executable, str(script), "--host", "127.0.0.1", "--port", str(PORT),
        "--data-dir", str(data_dir), "--deploy-secret", AUTH, "--admin-secret", ADMIN,
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    import urllib.error, urllib.request
    for _ in range(120):
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"staging exited during startup: {out}")
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=0.25) as r:
                if r.status == 200:
                    return proc
        except Exception:
            pass
        time.sleep(.05)
    proc.terminate()
    try: proc.wait(timeout=2)
    except Exception: proc.kill()
    out = proc.stdout.read() if proc.stdout else ""
    raise RuntimeError(f"staging failed to start: {out}")


def reset(deployment_id):
    reason = "canonical-10k"
    mac = hmac.new(ADMIN.encode(), f"RESET|{deployment_id}|{reason}".encode(), hashlib.sha256).hexdigest()
    return http_json("POST", "/staging/reset", {"deployment_id": deployment_id, "reason": reason, "mac": mac})


def make_kernel(store_path):
    store = Store(store_path, SECRET)
    state = SystemState(0, {"human": {"root": frozenset({"WRITE", "READ"})}}, {})
    store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), state.canonical(), "REFBOOT"))
    return store, Kernel(store, SECRET, boot_id="REFBOOT")


def prepare(store, kernel, req, params):
    s = store._read()
    cap = kernel.issue_protected(
        "human", "root", "WRITE",
        SystemState(s.epoch + 1, {"human": {"root": frozenset({"WRITE", "READ"})}}, {}),
        nonce=uuid.uuid4().hex, params=params, effect_id=req.effect_id,
        outcome_key=req.outcome_key,
    )
    return cap, store._read().epoch


class Journal:
    def __init__(self): self.rows = []
    def append(self, row): self.rows.append(dict(row))
    def _validated_state(self): return {r["key"]: dict(r) for r in self.rows}


def persist_evidence(path, evidence):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main():
    evidence = {"iterations": N, "completed": 0, "normal_pass": 0, "refusal_pass": 0,
                "replay_pass": 0, "failures": [], "environment": {}}
    evidence_path = Path(__file__).resolve().parent / "canonical-10k-evidence.json"
    persist_evidence(evidence_path, evidence)
    with tempfile.TemporaryDirectory(prefix="dar-10k-") as td:
        data_dir = Path(td) / "staging"
        data_dir.mkdir()
        proc = start_staging(data_dir)
        try:
            deployment_id = "canonical-10k"
            st, body = reset(deployment_id)
            if st != 200 or not body.get("ok"):
                raise RuntimeError(f"initial reset failed: {st} {body}")
            evidence["environment"] = {"python": sys.version.split()[0], "port": PORT,
                                        "secret_source": "environment" if os.environ.get("STAGING_DEPLOY_SECRET") else "ephemeral-generated"}
            persist_evidence(evidence_path, evidence)
            print(f"CANONICAL_10K_START iterations={N}", flush=True)
            for i in range(N):
                # A: normal protected deployment must create exactly the expected effect.
                art = f"canonical-artifact-{i}".encode()
                req = DeploymentRequest(art, "ci-staging", f"canonical-{i}")
                params = {"deployment_id": req.deployment_id, "artifact_digest": req.artifact_digest,
                          "staging_target": req.staging_target, "label": req.label,
                          "artifact_b64": base64.b64encode(art).decode()}
                with tempfile.TemporaryDirectory(prefix="dar-10k-store-") as sd:
                    store, kernel = make_kernel(Path(sd) / "state")
                    gate = EffectGate(kernel)
                    adapter = StagingDeploymentAdapter(BASE, AUTH)
                    cap, epoch = prepare(store, kernel, req, params)
                    adapter.fences[req.outcome_key] = epoch
                    gate.execute_protected(EffectRequest(cap, "human", "root", "WRITE", req.effect_id,
                                                          "WRITE", req.outcome_key), adapter, params, Journal())
                    obs = adapter.observe_staging(req.deployment_id)
                    if obs.get("state") != "DEPLOYED" or obs.get("artifact_digest") != req.artifact_digest:
                        raise AssertionError(f"normal effect mismatch at {i}: {obs}")
                    evidence["normal_pass"] += 1

                # B/C: valid refusal must survive local adapter state loss and block replay.
                refused = DeploymentRequest(f"refused-{i}".encode(), "ci-staging", f"refused-{i}")
                p = {"deployment_id": refused.deployment_id, "artifact_digest": refused.artifact_digest,
                     "staging_target": refused.staging_target, "label": refused.label,
                     "artifact_b64": base64.b64encode(refused.artifact_bytes).decode()}
                with tempfile.TemporaryDirectory(prefix="dar-10k-refusal-") as sd:
                    store, kernel = make_kernel(Path(sd) / "state")
                    gate = EffectGate(kernel)
                    adapter = StagingDeploymentAdapter(BASE, AUTH)
                    cap, epoch = prepare(store, kernel, refused, p)
                    adapter.fences[refused.outcome_key] = epoch
                    authority = RefusalAuthority(store, {"human": SECRET})
                    refusal = authority.issue_protected("human", refused.effect_id, cap.txid,
                                                        refused.outcome_key, target_epoch=epoch + 1)
                    authority.commit_protected(refusal, adapter)
                    try:
                        gate.execute_protected(EffectRequest(cap, "human", "root", "WRITE", refused.effect_id,
                                                              "WRITE", refused.outcome_key), adapter, p, Journal())
                        raise AssertionError(f"protected execution succeeded after refusal at {i}")
                    except AssertionError:
                        raise
                    except Exception:
                        pass
                    obs = adapter.observe_staging(refused.deployment_id)
                    if obs.get("state") == "DEPLOYED":
                        raise AssertionError(f"refused deployment occurred at {i}: {obs}")
                    evidence["refusal_pass"] += 1
                    adapter.refusals.clear(); adapter.fences.clear()
                    try:
                        adapter.commit("replay-" + uuid.uuid4().hex, refused.outcome_key, epoch, p)
                        raise AssertionError(f"replay succeeded after local state wipe at {i}")
                    except AssertionError:
                        raise
                    except Exception:
                        pass
                    obs2 = adapter.observe_staging(refused.deployment_id)
                    if obs2.get("state") == "DEPLOYED":
                        raise AssertionError(f"replay deployed after refusal at {i}: {obs2}")
                    evidence["replay_pass"] += 1

                evidence["completed"] = i + 1
                if (i + 1) % 100 == 0 or i + 1 == N:
                    persist_evidence(evidence_path, evidence)
                    print(f"CANONICAL_10K_PROGRESS completed={i+1}/{N} normal={evidence['normal_pass']} refusal={evidence['refusal_pass']} replay={evidence['replay_pass']}", flush=True)
            evidence["status"] = "PASS"
            persist_evidence(evidence_path, evidence)
            print(json.dumps(evidence, sort_keys=True), flush=True)
            return 0
        except Exception as exc:
            evidence["status"] = "FAIL"
            evidence["failures"].append({"type": type(exc).__name__, "message": str(exc), "completed": evidence["completed"]})
            persist_evidence(evidence_path, evidence)
            print(json.dumps(evidence, sort_keys=True), flush=True)
            return 1
        finally:
            proc.terminate()
            try: proc.wait(timeout=2)
            except Exception: proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
