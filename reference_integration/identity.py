"""Deterministic identity binding for reference staging deployments."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


def _h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_digest(artifact_bytes: bytes) -> str:
    return _h(artifact_bytes)


def deployment_id(*, artifact_digest: str, staging_target: str, label: str) -> str:
    payload = json.dumps(
        {
            "artifact_digest": artifact_digest,
            "staging_target": staging_target,
            "label": label,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return _h(payload)[:32]


def outcome_key_for_deployment(deployment_id: str) -> str:
    if len(deployment_id) != 32 or any(c not in "0123456789abcdef" for c in deployment_id):
        raise ValueError("deployment_id must be 32 lowercase hex chars")
    return deployment_id


def effect_id_for_deployment(deployment_id: str) -> str:
    return _h(f"effect:{deployment_id}".encode())[:6]


@dataclass(frozen=True)
class DeploymentRequest:
    artifact_bytes: bytes
    staging_target: str
    label: str

    @property
    def artifact_digest(self) -> str:
        return artifact_digest(self.artifact_bytes)

    @property
    def deployment_id(self) -> str:
        return deployment_id(
            artifact_digest=self.artifact_digest,
            staging_target=self.staging_target,
            label=self.label,
        )

    @property
    def outcome_key(self) -> str:
        return outcome_key_for_deployment(self.deployment_id)

    @property
    def effect_id(self) -> str:
        return effect_id_for_deployment(self.deployment_id)
