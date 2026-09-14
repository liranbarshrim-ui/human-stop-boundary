#!/usr/bin/env python3
"""Black-box verification of a live DAR external authority."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("DAR_EXTERNAL_AUTHORITY_URL", "").rstrip("/")
if not BASE:
    raise SystemExit("DAR_EXTERNAL_AUTHORITY_URL is required")


def call(path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    started = time.time()
    status, body = call("/health")
    require(status == 200 and body.get("ok") is True, f"health failed: {status} {body}")

    suffix = uuid.uuid4().hex
    refused = f"dar-refused-{suffix}"
    live = f"dar-live-{suffix}"
    rollback = f"dar-rollback-{suffix}"

    status, body = call("/fence", {"outcome": live, "epoch": 1})
    require(status == 200 and body.get("ok") is True, f"live fence failed: {status} {body}")
    idem_live = f"commit-{suffix}-live"
    status, body = call("/commit", {"outcome": live, "epoch": 1, "idempotency_key": idem_live})
    require(status == 200 and body.get("ok") is True and body.get("idempotent") is False,
            f"initial commit failed: {status} {body}")
    status, body = call("/commit", {"outcome": live, "epoch": 1, "idempotency_key": f"commit-{suffix}-duplicate"})
    require(status == 409 and body.get("error") == "outcome_already_committed",
            f"duplicate outcome unexpectedly accepted: {status} {body}")
    status, body = call("/refuse", {"outcome": live, "epoch": 1, "refusal_id": f"refusal-{suffix}-late"})
    require(status == 200 and body.get("ok") is True, f"late refusal failed: {status} {body}")

    status, body = call("/refuse", {"outcome": refused, "epoch": 7, "refusal_id": f"refusal-{suffix}"})
    require(status == 200 and body.get("ok") is True and body.get("idempotent") is False,
            f"refusal failed: {status} {body}")
    status, body = call("/refuse", {"outcome": refused, "epoch": 7, "refusal_id": f"refusal-{suffix}"})
    require(status == 200 and body.get("ok") is True and body.get("idempotent") is True,
            f"refusal retry not idempotent: {status} {body}")
    status, body = call("/commit", {"outcome": refused, "epoch": 7, "idempotency_key": f"commit-{suffix}-1"})
    require(status == 409 and body.get("error") == "terminal_refusal",
            f"refused commit unexpectedly accepted: {status} {body}")
    status, body = call("/commit", {"outcome": refused, "epoch": 7, "idempotency_key": f"commit-{suffix}-2"})
    require(status == 409 and body.get("error") == "terminal_refusal",
            f"new idem bypassed refusal: {status} {body}")

    status, body = call("/fence", {"outcome": rollback, "epoch": 9})
    require(status == 200, f"rollback setup failed: {status} {body}")
    status, body = call("/fence", {"outcome": rollback, "epoch": 8})
    require(status == 409 and body.get("error") == "fence_rollback",
            f"fence rollback accepted: {status} {body}")

    status, state = call("/state")
    require(status == 200, f"state failed: {status} {state}")
    require(state.get("effects", {}).get(idem_live, {}).get("outcome") == live,
            "committed outcome missing from authoritative state")
    require(refused in state.get("refusals", {}), "terminal refusal missing from authoritative state")
    require(state.get("committed_outcomes", {}).get(live) == idem_live,
            "committed outcome index missing from authoritative state")

    evidence = {
        "evidence_type": "external-authority-black-box-verification",
        "base_url": BASE,
        "hostname": BASE.split("//", 1)[-1].split("/", 1)[0],
        "checked_at_unix": time.time(),
        "duration_seconds": round(time.time() - started, 3),
        "tests": {
            "health": "PASS",
            "commit_before_refusal_nonretroactive": "PASS",
            "refusal_retry_idempotent": "PASS",
            "refusal_blocks_commit": "PASS",
            "new_idempotency_key_cannot_bypass_refusal": "PASS",
            "duplicate_protected_outcome_rejected": "PASS",
            "fence_rollback_rejected": "PASS",
            "authoritative_state_observed": "PASS",
        },
        "verdict": "PASS",
        "scope": "deployment-level black-box evidence; not a production certification",
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
# Trigger live external-authority evidence after the deployed authority update.
