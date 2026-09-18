import hashlib
import hmac
import json
import os
import sys
import threading
import time
import uuid
from http.client import HTTPConnection
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

AUTH_SECRET = "transport-secret"
INTENT_SECRET = "intent-secret"
PRINCIPAL = "test-principal"

os.environ["DAR_PERSISTENCE_MODE"] = "memory"
os.environ["DAR_AUTH_CREDENTIALS_JSON"] = json.dumps({PRINCIPAL: AUTH_SECRET})
os.environ["DAR_INTENT_CREDENTIALS_JSON"] = json.dumps({PRINCIPAL: INTENT_SECRET})

import external_authority_server as srv
from postgres_authority import PostgresAuthority


@pytest.fixture(autouse=True)
def reset_state():
    with srv.lock:
        srv.replay_nonces.clear()
        srv.intent_replay_nonces.clear()
        srv.fences.clear()
        srv.refusals.clear()
        srv.effects.clear()
        srv.committed_outcomes.clear()
    yield


def intent(operation, outcome, epoch, refusal_id="", idempotency_key=""):
    issued_at = int(time.time())
    nonce = uuid.uuid4().hex
    canonical = "|".join(
        (
            PRINCIPAL,
            operation,
            outcome,
            str(epoch),
            str(refusal_id),
            str(idempotency_key),
            str(issued_at),
            nonce,
        )
    ).encode()
    return {
        "principal": PRINCIPAL,
        "operation": operation,
        "outcome": outcome,
        "epoch": epoch,
        "issued_at": issued_at,
        "nonce": nonce,
        "refusal_id": refusal_id,
        "idempotency_key": idempotency_key,
        "mac": hmac.new(INTENT_SECRET.encode(), canonical, hashlib.sha256).hexdigest(),
    }


def headers(body, method="POST", path="/commit", nonce=None, timestamp=None):
    timestamp = str(timestamp if timestamp is not None else int(time.time()))
    nonce = nonce or uuid.uuid4().hex
    canonical = srv._canonical_transport(method, path, timestamp, nonce, body)
    signature = hmac.new(AUTH_SECRET.encode(), canonical, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "X-DAR-Principal": PRINCIPAL,
        "X-DAR-Timestamp": timestamp,
        "X-DAR-Nonce": nonce,
        "X-DAR-Signature": signature,
    }, nonce


@pytest.fixture
def server():
    httpd = srv.ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def request(server, method, path, payload=None, auth=True, transport_only=False, timestamp=None, nonce=None):
    if method.upper() == "GET" and payload is None:
        body = b""
    else:
        body = json.dumps(payload or {}, sort_keys=True, separators=(",", ":")).encode()
    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    hdrs = {"Content-Length": str(len(body))}
    if auth:
        signed, nonce = headers(body, method, path, nonce=nonce, timestamp=timestamp)
        hdrs.update(signed)
    if transport_only and payload is not None:
        payload = dict(payload)
        payload.pop("authority_intent", None)
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        hdrs, nonce = headers(body, method, path, nonce=nonce, timestamp=timestamp)
    conn.request(method, path, body=body, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, json.loads(raw), nonce


def authorized_payload(operation, outcome="o1", epoch=1, refusal_id="r1", idem="i1"):
    return {
        "outcome": outcome,
        "epoch": epoch,
        "refusal_id": refusal_id,
        "idempotency_key": idem,
        "authority_intent": intent(operation, outcome, epoch, refusal_id, idem),
    }


def test_unauthorized_fence_rejected(server):
    status, body, _ = request(server, "POST", "/fence", {"outcome": "o1", "epoch": 99}, auth=False)
    assert status == 401
    assert body["error"] == "missing_auth"


def test_unauthorized_refuse_rejected(server):
    status, body, _ = request(server, "POST", "/refuse", {"outcome": "o1", "epoch": 1, "refusal_id": "r1"}, auth=False)
    assert status == 401
    assert body["error"] == "missing_auth"


def test_unauthorized_commit_rejected(server):
    status, body, _ = request(server, "POST", "/commit", {"outcome": "o1", "epoch": 1, "idempotency_key": "i1"}, auth=False)
    assert status == 401
    assert body["error"] == "missing_auth"


def test_unauthorized_state_rejected(server):
    status, body, _ = request(server, "GET", "/state", {}, auth=False)
    assert status == 401
    assert body["error"] == "missing_auth"


def test_missing_and_malformed_auth_rejected(server):
    status, body, _ = request(server, "POST", "/commit", {"outcome": "o1", "epoch": 1, "idempotency_key": "i1"}, auth=False)
    assert status == 401
    assert body["error"] == "missing_auth"

    payload = authorized_payload("commit")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    bad = {"Content-Type": "application/json", "Content-Length": str(len(raw)), "X-DAR-Principal": PRINCIPAL}
    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("POST", "/commit", body=raw, headers=bad)
    resp = conn.getresponse()
    assert resp.status == 401
    assert json.loads(resp.read())["error"] == "missing_auth"
    conn.close()


def test_valid_transport_without_intent_cannot_mutate(server):
    payload = {"outcome": "o1", "epoch": 1, "idempotency_key": "i1"}
    status, body, _ = request(server, "POST", "/commit", payload, auth=True, transport_only=True)
    assert status == 401
    assert body["error"] == "missing_authority_intent"
    status, state, _ = request(server, "GET", "/state", None, auth=True)
    assert status == 200
    assert state["effects"] == {}


def test_valid_requests_work(server):
    status, body, _ = request(server, "POST", "/fence", authorized_payload("fence", epoch=1))
    assert status == 200 and body["ok"] is True
    status, body, _ = request(server, "POST", "/commit", authorized_payload("commit", epoch=1), auth=True)
    assert status == 200 and body["ok"] is True


def test_authority_intent_is_bound_to_operation(server):
    payload = authorized_payload("fence", epoch=1)
    status, body, _ = request(server, "POST", "/commit", payload)
    assert status == 401
    assert body["error"] == "invalid_authority_intent"


def test_authority_intent_nonce_replay_is_rejected_even_with_new_transport_nonce(server):
    payload = authorized_payload("fence", outcome="replay-target", epoch=1)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    first_headers, _ = headers(body, "POST", "/fence")
    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("POST", "/fence", body=body, headers=first_headers)
    first = conn.getresponse()
    assert first.status == 200
    first.read()
    conn.close()

    second_headers, _ = headers(body, "POST", "/fence")
    assert second_headers["X-DAR-Nonce"] != first_headers["X-DAR-Nonce"]
    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("POST", "/fence", body=body, headers=second_headers)
    second = conn.getresponse()
    assert second.status == 409
    assert json.loads(second.read())["error"] == "intent_replay_detected"
    conn.close()


def test_postgres_idempotency_retry_requires_matching_epoch():
    class FakeResult:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class FakeConnection:
        def __init__(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params=()):
            self.calls.append((sql, params))
            if "pg_advisory_xact_lock" in sql:
                return FakeResult()
            if "FROM dar_refusals" in sql:
                return FakeResult(None)
            if "SELECT fence FROM dar_fences" in sql:
                return FakeResult({"fence": 2})
            if "SELECT outcome_key, epoch FROM dar_effects" in sql:
                return FakeResult({"outcome_key": "o1", "epoch": 1})
            raise AssertionError(f"unexpected SQL: {sql}")

    fake = FakeConnection()
    authority = object.__new__(PostgresAuthority)
    authority.dsn = "unused"
    authority._connect = lambda: fake

    status, body = authority.commit("o1", 2, "idem-1")
    assert status == 409
    assert body == {"ok": False, "error": "idempotency_key_reuse"}


def test_no_legacy_v1_fallback(server):
    payload = {"outcome": "o1", "epoch": 1, "idempotency_key": "i1"}
    for path in ("/fence", "/refuse", "/commit"):
        status, body, _ = request(server, "POST", path, payload, auth=False)
        assert status == 401
        assert body["error"] == "missing_auth"


def test_state_requires_transport_auth_only(server):
    payload = authorized_payload("fence", epoch=1)
    status, _, _ = request(server, "POST", "/fence", payload)
    assert status == 200
    status, body, _ = request(server, "GET", "/state", None, auth=True)
    assert status == 200
    assert "fences" in body


def test_replay_is_rejected(server):
    payload = authorized_payload("fence", epoch=1)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    hdrs, nonce = headers(body, "POST", "/fence")
    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("POST", "/fence", body=body, headers=hdrs)
    first = conn.getresponse()
    assert first.status == 200
    first.read()
    conn.close()
    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("POST", "/fence", body=body, headers=hdrs)
    second = conn.getresponse()
    assert second.status == 409
    assert json.loads(second.read())["error"] == "replay_detected"
    conn.close()
    assert nonce
