"""External monotonic witness backed by the public Rekor transparency log.

This adapter deliberately does not claim that Rekor is a transaction/serialization
authority. It gives DAR an externally witnessed, append-only sequence that can be
used as a monotonic floor. Protected commit semantics must still bind their
linearization point to an external serialization authority before the v37 gate can
be marked PASS.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REKOR_URL = "https://rekor.sigstore.dev"


@dataclass(frozen=True)
class RekorAnchorRecord:
    uuid: str
    log_index: int
    tree_size: int
    digest: str


class RekorMonotonicAnchor:
    def __init__(self, server: str = DEFAULT_REKOR_URL) -> None:
        self.server = server.rstrip("/")
        self._floor = -1

    def floor(self) -> int:
        return self._floor

    def advance_to(self, sequence: int) -> None:
        if sequence < self._floor:
            raise ValueError("external anchor rollback")
        self._floor = sequence

    def _post_entry(self, payload: dict) -> dict:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        req = urllib.request.Request(
            self.server + "/api/v1/log/entries",
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    def publish(self, message: bytes) -> RekorAnchorRecord:
        digest = hashlib.sha256(message).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact = root / "anchor.bin"
            key = root / "key.pem"
            pub = root / "pub.pem"
            sig = root / "sig.bin"
            artifact.write_bytes(message)
            subprocess.run(
                ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(key)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["openssl", "ec", "-in", str(key), "-pubout", "-out", str(pub)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", str(key), "-out", str(sig), str(artifact)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            payload = {
                "apiVersion": "0.0.1",
                "kind": "hashedrekord",
                "spec": {
                    "data": {"hash": {"algorithm": "sha256", "value": digest}},
                    "signature": {
                        "content": base64.b64encode(sig.read_bytes()).decode(),
                        "publicKey": {"content": base64.b64encode(pub.read_bytes()).decode()},
                    },
                },
            }
            response = self._post_entry(payload)
        uuid = next(iter(response))
        entry = response[uuid]
        log_index = int(entry["logIndex"])
        tree_size = int(entry["verification"]["signedEntryTimestamp"]["integratedTime"] if False else entry.get("logIndex", 0))
        self.advance_to(log_index)
        return RekorAnchorRecord(uuid, log_index, tree_size, digest)
