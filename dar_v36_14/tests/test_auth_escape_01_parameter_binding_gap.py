from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from http.client import HTTPConnection

from dar_v36_14 import external_authority_server as eas


PRINCIPAL = "parameter-binding-gap-test"
AUTH_SECRET = "transport-secret-parameter-binding-gap"
INTENT_SECRET = "intent-secret-parameter-binding-gap"


def _transport_signature(method: str, path: str, timestamp: str, nonce: str, body: bytes) -> str:
    digest = hashlib.sha256(body).hexdigest()
    canonical = "|".join((method.upper(), path, timestamp, nonce, digest)).encode()
    return hmac.new(AUTH_SECRET.encode(), canonical, hashlib.sha256).hexdigest()


def _intent_mac(
    *,
    operation: str,
    outcome: str,
    epoch: int,
    issued_at: int,
    nonce: str,
) -> str:
    canonical = "|".join(
        (
            PRINCIPAL,
            operation,
            outcome,
            str(epoch),
            "",
            "",
            str(issued_at),
            nonce,
        )
    ).encode()
    return hmac.new(INTENT_SECRET.encode(), canonical, hashlib.sha256).hexdigest()


def _request(path: str, payload: dict, *, intent_epoch: int) -> tuple[int, dict]:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    transport_nonce = uuid.uuid4().hex
    intent_nonce = uuid.uuid4().hex
    payload["authority_intent"] = {
        "principal": PRINCIPAL,
        "operation": path.lstrip("/"),
        "outcome": payload["outcome"],
        "epoch": intent_epoch,
        "issued_at": int(timestamp),
        "nonce": intent_nonce,
        "mac": _intent_mac(
            operation=path.lstrip("/"),
            outcome=payload["outcome"],
            epoch=intent_epoch,
            issued_at=int(timestamp),
            nonce=intent_nonce,
        ),
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "X-DAR-Principal": PRINCIPAL,
        "X-DAR-Timestamp": timestamp,
        "X-DAR-Nonce": transport_nonce,
        "X-DAR-Signature": _transport_signature("POST", path, timestamp, transport_nonce, body),
    }
    connection = HTTPConnection("127.0.0.1", TEST_PORT, timeout=5)
    try:
        connection.request("POST", path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        return response.status, json.loads(raw or b"{}")
    finally:
        connection.close()


TEST_SERVER = None
TEST_PORT = None


@contextmanager
def _server():
    global TEST_SERVER, TEST_PORT
    server = eas.ThreadingHTTPServer(("127.0.0.1", 0), eas.Handler)
    TEST_SERVER = server
    TEST_PORT = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        TEST_SERVER = None
        TEST_PORT = None


def test_outer_epoch_cannot_diverge_from_signed_intent_epoch():
    outcome = f"parameter-binding-gap-{uuid.uuid4().hex}"
    signed_epoch = 10
    outer_epoch = 999999999

    old_auth = eas.AUTH_CREDENTIALS
    old_intent = eas.INTENT_CREDENTIALS
    old_fences = eas.fences
    old_refusals = eas.refusals
    old_effects = eas.effects
    old_committed = eas.committed_outcomes
    try:
        eas.AUTH_CREDENTIALS = {PRINCIPAL: AUTH_SECRET}
        eas.INTENT_CREDENTIALS = {PRINCIPAL: INTENT_SECRET}
        eas.fences = {}
        eas.refusals = {}
        eas.effects = {}
        eas.committed_outcomes = {}

        with _server():
            before = _request(
                "/fence",
                {"outcome": outcome, "epoch": signed_epoch},
                intent_epoch=signed_epoch,
            )
            assert before[0] == 200

            status, state_before = _state(outcome)
            assert status == 200
            assert state_before["fences"].get(outcome) == signed_epoch

            status, body = _request(
                "/fence",
                {"outcome": outcome, "epoch": outer_epoch},
                intent_epoch=signed_epoch,
            )
            print(
                "RAW_PARAMETER_BINDING_GAP_FENCE "
                + json.dumps(
                    {
                        "status": status,
                        "body": body,
                        "signed_intent_epoch": signed_epoch,
                        "outer_epoch": outer_epoch,
                    },
                    sort_keys=True,
                )
            )
            assert status == 200

            status, state_after = _state(outcome)
            assert status == 200
            print(
                "RAW_PARAMETER_BINDING_GAP_STATE "
                + json.dumps(
                    {
                        "before_fence": state_before["fences"].get(outcome),
                        "after_fence": state_after["fences"].get(outcome),
                    },
                    sort_keys=True,
                )
            )
            assert state_after["fences"].get(outcome) == outer_epoch
            assert state_after["fences"].get(outcome) != signed_epoch
    finally:
        eas.AUTH_CREDENTIALS = old_auth
        eas.INTENT_CREDENTIALS = old_intent
        eas.fences = old_fences
        eas.refusals = old_refusals
        eas.effects = old_effects
        eas.committed_outcomes = old_committed


def _state(outcome: str) -> tuple[int, dict]:
    body = b""
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    digest = hashlib.sha256(body).hexdigest()
    canonical = "|".join(("GET", "/state", timestamp, nonce, digest)).encode()
    signature = hmac.new(AUTH_SECRET.encode(), canonical, hashlib.sha256).hexdigest()
    connection = HTTPConnection("127.0.0.1", TEST_PORT, timeout=5)
    try:
        connection.request(
            "GET",
            "/state",
            body=body,
            headers={
                "Content-Length": "0",
                "X-DAR-Principal": PRINCIPAL,
                "X-DAR-Timestamp": timestamp,
                "X-DAR-Nonce": nonce,
                "X-DAR-Signature": signature,
            },
        )
        response = connection.getresponse()
        raw = response.read()
        state = json.loads(raw or b"{}")
        return response.status, state
    finally:
        connection.close()
