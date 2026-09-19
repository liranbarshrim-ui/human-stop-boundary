#!/usr/bin/env python3
"""Isolated staging service — deploy only with valid authority-minted token.

Refused deployment_ids are stored and rejected for this process/data dir.
Unauthenticated /staging/deploy and /staging/reset are rejected (401).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac as hm
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from staging_auth import verify_deploy_token

LOCK = threading.RLock()
DEPLOYMENTS: dict = {}
REFUSALS: dict = {}
USED_TOKENS: set = set()
DATA_FILE: Path | None = None
AUTH_SECRET: bytes = b""


def _save() -> None:
    if DATA_FILE is None:
        return
    DATA_FILE.write_text(json.dumps({"deployments": DEPLOYMENTS, "refusals": REFUSALS, "used_tokens": sorted(USED_TOKENS)}, indent=2, sort_keys=True))


def _load() -> None:
    global DEPLOYMENTS, REFUSALS, USED_TOKENS
    if DATA_FILE and DATA_FILE.exists():
        raw = json.loads(DATA_FILE.read_text() or "{}")
        DEPLOYMENTS = raw.get("deployments", {})
        REFUSALS = raw.get("refusals", {})
        USED_TOKENS = set(raw.get("used_tokens", []))


def _valid_admin_mac(body: dict, purpose: str) -> bool:
    mac = str(body.get("mac", ""))
    canonical = f"{purpose}|{body.get('deployment_id','')}|{body.get('reason','') or ''}".encode()
    expected = hm.new(AUTH_SECRET, canonical, hashlib.sha256).hexdigest()
    return bool(mac) and hm.compare_digest(expected, mac)


def deploy(body: dict) -> tuple[int, dict]:
    try:
        deployment_id = body["deployment_id"]
        artifact_digest = body["artifact_digest"]
        artifact_b64 = body["artifact_b64"]
        label = body.get("label", "")
        staging_target = body.get("staging_target", "local-staging")
        token = body.get("deploy_authorization")
    except KeyError as e:
        return 400, {"ok": False, "error": f"missing_{e}"}
    if not token or not isinstance(token, dict):
        return 401, {"ok": False, "error": "missing_deploy_authorization"}
    err = verify_deploy_token(secret=AUTH_SECRET, token=token, deployment_id=deployment_id, artifact_digest=artifact_digest)
    if err:
        return 401, {"ok": False, "error": err}
    raw = base64.b64decode(artifact_b64)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != artifact_digest:
        return 400, {"ok": False, "error": "artifact_digest_mismatch", "actual": actual}
    with LOCK:
        if deployment_id in REFUSALS:
            return 403, {"ok": False, "error": "terminal_refusal", "refusal": REFUSALS[deployment_id]}
        existing = DEPLOYMENTS.get(deployment_id)
        if existing and existing.get("state") == "DEPLOYED":
            if existing.get("artifact_digest") == artifact_digest:
                return 200, {"ok": True, "idempotent": True, **existing}
            return 409, {"ok": False, "error": "deployment_id_conflict"}
        idem = str(token.get("idempotency_key", ""))
        if idem:
            USED_TOKENS.add(idem)
        record = {"deployment_id": deployment_id, "artifact_digest": artifact_digest, "staging_target": staging_target, "label": label, "state": "DEPLOYED", "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "artifact_size": len(raw), "fence_epoch": int(token["fence_epoch"])}
        DEPLOYMENTS[deployment_id] = record
        _save()
        return 200, {"ok": True, "idempotent": False, **record}


def refuse(body: dict) -> tuple[int, dict]:
    try:
        deployment_id = body["deployment_id"]
        fence_epoch = int(body["fence_epoch"])
        refusal_id = body["refusal_id"]
        mac = body.get("mac", "")
    except Exception:
        return 400, {"ok": False, "error": "invalid_refuse"}
    canonical = f"REFUSE|{deployment_id}|{fence_epoch}|{refusal_id}".encode()
    expected = hm.new(AUTH_SECRET, canonical, hashlib.sha256).hexdigest()
    if not hm.compare_digest(expected, str(mac)):
        return 401, {"ok": False, "error": "invalid_refuse_mac"}
    with LOCK:
        REFUSALS[deployment_id] = {"fence_epoch": fence_epoch, "refusal_id": refusal_id, "refused_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _save()
    return 200, {"ok": True, "deployment_id": deployment_id}


def reset(body: dict) -> tuple[int, dict]:
    if not _valid_admin_mac(body, "RESET"):
        return 401, {"ok": False, "error": "invalid_reset_mac"}
    with LOCK:
        DEPLOYMENTS.clear()
        REFUSALS.clear()
        USED_TOKENS.clear()
        _save()
    return 200, {"ok": True, "state": "empty"}


def status(deployment_id: str) -> tuple[int, dict]:
    with LOCK:
        if deployment_id in REFUSALS and deployment_id not in DEPLOYMENTS:
            return 200, {"deployment_id": deployment_id, "state": "NOT_DEPLOYED", "artifact_digest": None, "staging_target": None, "deployed_at": None, "refused": True, "refusal": REFUSALS[deployment_id]}
        rec = DEPLOYMENTS.get(deployment_id)
        if not rec:
            return 200, {"deployment_id": deployment_id, "state": "NOT_DEPLOYED", "artifact_digest": None, "staging_target": None, "deployed_at": None}
        out = dict(rec)
        if deployment_id in REFUSALS:
            out["refused"] = True
            out["refusal"] = REFUSALS[deployment_id]
        return 200, out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass
    def _read_json(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        return json.loads(self.rfile.read(n).decode() if n else "{}")
    def _reply(self, code: int, body: dict) -> None:
        data = json.dumps(body, sort_keys=True).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            return self._reply(200, {"ok": True, "service": "reference-staging", "auth": "required_for_deploy_and_reset"})
        if path.startswith("/staging/status/"):
            code, body = status(path[len("/staging/status/"):].strip("/"))
            return self._reply(code, body)
        return self._reply(404, {"error": "not_found"})
    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()
        if path == "/staging/deploy":
            code, response = deploy(body)
            return self._reply(code, response)
        if path == "/staging/refuse":
            code, response = refuse(body)
            return self._reply(code, response)
        if path == "/staging/reset":
            code, response = reset(body)
            return self._reply(code, response)
        return self._reply(404, {"error": "not_found"})


def main() -> None:
    global DATA_FILE, AUTH_SECRET
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=19090)
    ap.add_argument("--data-dir", default="")
    ap.add_argument("--secret", default=os.environ.get("STAGING_AUTH_SECRET", ""))
    args = ap.parse_args()
    if not args.secret:
        ap.error("--secret or STAGING_AUTH_SECRET is required")
    AUTH_SECRET = args.secret.encode()
    if args.data_dir:
        DATA_FILE = Path(args.data_dir) / "staging_state.json"
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _load()
    print(f"staging listening on http://{args.host}:{args.port} (deploy/reset auth required)", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
