"""Reference Deployment Adapter: fence/refusal + authorized staging deploy only."""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import urllib.error
import urllib.request
from typing import Any

from dar_v36_14.dar.effect_transaction import FencedEffectAdapter, TxnStatus
from staging_auth import mint_deploy_token


class StagingDeploymentAdapter(FencedEffectAdapter):
    def __init__(self, staging_base: str, auth_secret: str | bytes):
        if not auth_secret:
            raise ValueError("staging auth secret is required")
        self.staging_base = staging_base.rstrip("/")
        self.auth_secret = auth_secret.encode() if isinstance(auth_secret, str) else auth_secret
        self._lock = threading.RLock()
        self.fences: dict[str, int] = {}
        self.refusals: dict[str, tuple[int, str]] = {}
        self.committed: dict[str, str] = {}

    def current_fence(self, outcome_key: str) -> int:
        with self._lock:
            return int(self.fences.get(outcome_key, 0))

    def is_refused(self, outcome_key: str) -> bool:
        with self._lock:
            return outcome_key in self.refusals

    def refuse_outcome(self, outcome_key: str, fence_epoch: int, refusal_id: str) -> None:
        with self._lock:
            current = int(self.fences.get(outcome_key, 0))
            if current > int(fence_epoch):
                raise ValueError("fence rollback")
            existing = self.refusals.get(outcome_key)
            if existing and existing != (int(fence_epoch), refusal_id):
                raise ValueError("conflicting refusal")
            self.fences[outcome_key] = int(fence_epoch)
            self.refusals[outcome_key] = (int(fence_epoch), refusal_id)
        canonical = f"REFUSE|{outcome_key}|{int(fence_epoch)}|{refusal_id}".encode()
        mac = hmac.new(self.auth_secret, canonical, hashlib.sha256).hexdigest()
        code, body = self._http("POST", "/staging/refuse", {"deployment_id": outcome_key, "fence_epoch": int(fence_epoch), "refusal_id": refusal_id, "mac": mac})
        if code != 200 or not body.get("ok"):
            raise RuntimeError(f"staging refuse publish failed: {code} {body}")

    def _http(self, method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.staging_base + path, data=data, headers={"Content-Type": "application/json"}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw}

    def commit(self, idempotency_key: str, outcome_key: str, fence_epoch: int, params: dict) -> Any:
        with self._lock:
            if outcome_key in self.refusals:
                raise RuntimeError("outcome terminally refused")
            if int(self.fences.get(outcome_key, 0)) != int(fence_epoch):
                raise RuntimeError("fence advanced")
            if idempotency_key in self.committed:
                if self.committed[idempotency_key] == outcome_key:
                    return TxnStatus.COMMITTED
                raise RuntimeError("idempotency conflict")
            deployment_id = params.get("deployment_id")
            artifact_digest = params.get("artifact_digest")
            artifact_b64 = params.get("artifact_b64")
            if not deployment_id or not artifact_digest or not artifact_b64:
                raise RuntimeError("missing deployment params")
            if deployment_id != outcome_key:
                raise RuntimeError("outcome_key must equal deployment_id")
            token = mint_deploy_token(secret=self.auth_secret, deployment_id=deployment_id, artifact_digest=artifact_digest, fence_epoch=int(fence_epoch), idempotency_key=idempotency_key)
            code, body = self._http("POST", "/staging/deploy", {"deployment_id": deployment_id, "artifact_digest": artifact_digest, "artifact_b64": artifact_b64, "label": params.get("label", ""), "staging_target": params.get("staging_target", "local-staging"), "deploy_authorization": token})
            if code != 200 or not body.get("ok"):
                raise RuntimeError(f"staging deploy failed: {code} {body}")
            if body.get("state") != "DEPLOYED":
                raise RuntimeError(f"staging did not reach DEPLOYED: {body}")
            if body.get("artifact_digest") != artifact_digest:
                raise RuntimeError("staging returned different artifact_digest")
            self.committed[idempotency_key] = outcome_key
            return TxnStatus.COMMITTED

    def status(self, idempotency_key: str):
        with self._lock:
            return TxnStatus.COMMITTED if idempotency_key in self.committed else TxnStatus.UNKNOWN

    def execute(self, idempotency_key: str, params: dict):
        raise AssertionError("protected path must not call execute()")

    def observe_staging(self, deployment_id: str) -> dict:
        code, body = self._http("GET", f"/staging/status/{deployment_id}")
        if code != 200:
            return {"error": body, "http_status": code}
        return body
