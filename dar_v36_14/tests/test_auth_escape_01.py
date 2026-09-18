import base64
import hashlib
import hmac
import importlib.util
import json
import os
import threading
import time
import unittest
import uuid
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = b"t" * 32
AUTHORITY = b"a" * 32
os.environ["DAR_V2_TRANSPORT_KEYS"] = json.dumps({"transport-1": base64.b64encode(TRANSPORT).decode()})
os.environ["DAR_V2_AUTHORITY_KEYS"] = json.dumps({"human-a": base64.b64encode(AUTHORITY).decode()})
os.environ["DAR_AUTH_WINDOW_SECONDS"] = "300"
os.environ["DAR_PERSISTENCE_MODE"] = "memory"

spec = importlib.util.spec_from_file_location("auth_escape_server", ROOT / "dar_v36_14" / "external_authority_server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class AuthEscape01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=2)

    def setUp(self):
        with server.lock:
            server.used_transport_nonces.clear()
            server.fences.clear()
            server.refusals.clear()
            server.effects.clear()
            server.committed_outcomes.clear()

    def request(self, method, path, body=b"", auth=True, tamper_mac=False):
        if isinstance(body, dict):
            body = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        headers = {"Content-Length": str(len(body))}
        nonce = uuid.uuid4().hex
        if auth:
            timestamp = str(int(time.time()))
            message = server._transport_message(method, path, hashlib.sha256(body).hexdigest(), timestamp, nonce)
            mac = hmac.new(TRANSPORT, message, hashlib.sha256).hexdigest()
            if tamper_mac:
                mac = "0" * 64
            headers.update({"X-DAR-Key-Id": "transport-1", "X-DAR-Timestamp": timestamp, "X-DAR-Nonce": nonce, "X-DAR-MAC": mac})
        conn = HTTPConnection("127.0.0.1", self.port, timeout=3)
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode())
        conn.close()
        return resp.status, payload

    def authority_intent(self, operation, body):
        signed = dict(body)
        signed.pop("authority_intent", None)
        canonical = json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        mac = hmac.new(AUTHORITY, f"DAR-AUTH-V2\n{operation}\n{canonical}".encode(), hashlib.sha256).hexdigest()
        return {"principal": "human-a", "mac": mac}

    def refusal_intent(self, outcome, epoch=1):
        refusal_id = uuid.uuid4().hex
        issued_at = int(time.time())
        payload = server.RefusalAuthority._payload(refusal_id, "human-a", "effect-1", "tx-1", epoch, issued_at, outcome)
        mac = hmac.new(AUTHORITY, payload, hashlib.sha256).hexdigest()
        return {"refusal_id": refusal_id, "principal": "human-a", "effect_id": "effect-1", "capability_txid": "tx-1", "target_epoch": epoch, "issued_at": issued_at, "mac": mac, "outcome_key": outcome}

    def test_unauthorized_four_protected_endpoints_rejected(self):
        cases = [("POST", "/fence", {"outcome": "aa", "epoch": 1}), ("POST", "/refuse", {"outcome": "aa", "epoch": 1, "refusal_id": "r"}), ("POST", "/commit", {"outcome": "aa", "epoch": 1, "idempotency_key": "k"}), ("GET", "/state", b"")]
        for method, path, body in cases:
            status, payload = self.request(method, path, body, auth=False)
            self.assertEqual(status, 401, (path, payload))
            self.assertEqual(payload["wire_protocol"], "v2")

    def test_malformed_or_tampered_auth_rejected(self):
        status, _ = self.request("GET", "/state", auth=False)
        self.assertEqual(status, 401)
        status, payload = self.request("GET", "/state", tamper_mac=True)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "invalid_auth")

    def test_transport_credentials_without_authority_intent_cannot_mutate(self):
        for path, body in [("/fence", {"outcome": "aa", "epoch": 1}), ("/commit", {"outcome": "aa", "epoch": 1, "idempotency_key": "k"}), ("/refuse", {"outcome": "aa", "epoch": 1, "refusal_id": "r"})]:
            status, payload = self.request("POST", path, body)
            self.assertEqual(status, 403, (path, payload))
            self.assertEqual(payload["error"], "authority_intent_required")
        self.assertEqual(server.fences, {})
        self.assertEqual(server.refusals, {})
        self.assertEqual(server.effects, {})

    def test_authorized_v2_operations_execute(self):
        fence = {"outcome": "aa", "epoch": 1}
        fence["authority_intent"] = self.authority_intent("fence", fence)
        status, payload = self.request("POST", "/fence", fence)
        self.assertEqual(status, 200, payload)

        commit = {"outcome": "aa", "epoch": 1, "idempotency_key": "k"}
        commit["authority_intent"] = self.authority_intent("commit", commit)
        status, payload = self.request("POST", "/commit", commit)
        self.assertEqual(status, 200, payload)

        status, payload = self.request("POST", "/refuse", {"refusal_intent": self.refusal_intent("bb", 2)})
        self.assertEqual(status, 200, payload)

        status, payload = self.request("GET", "/state")
        self.assertEqual(status, 200, payload)
        self.assertIn("aa", payload["committed_outcomes"])
        self.assertIn("bb", payload["refusals"])

    def test_refusal_authority_verification_rejects_tampering(self):
        intent = self.refusal_intent("cc", 1)
        status, _ = self.request("POST", "/refuse", {"refusal_intent": intent})
        self.assertEqual(status, 200)
        intent["mac"] = "0" * 64
        status, payload = self.request("POST", "/refuse", {"refusal_intent": intent})
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "authority_intent_required")

    def test_no_legacy_v1_fallback(self):
        status, payload = self.request("POST", "/fence", {"outcome": "aa", "epoch": 1}, auth=False)
        self.assertEqual(status, 401)
        self.assertEqual(payload["wire_protocol"], "v2")

    def test_transport_replay_is_rejected(self):
        body = b""
        nonce = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        mac = hmac.new(TRANSPORT, server._transport_message("GET", "/state", hashlib.sha256(body).hexdigest(), timestamp, nonce), hashlib.sha256).hexdigest()
        headers = {"Content-Length": "0", "X-DAR-Key-Id": "transport-1", "X-DAR-Timestamp": timestamp, "X-DAR-Nonce": nonce, "X-DAR-MAC": mac}
        def call():
            conn = HTTPConnection("127.0.0.1", self.port, timeout=3)
            conn.request("GET", "/state", headers=headers)
            resp = conn.getresponse(); payload = json.loads(resp.read().decode()); conn.close(); return resp.status, payload
        first, _ = call()
        second, payload = call()
        self.assertEqual(first, 200)
        self.assertEqual(second, 401)
        self.assertEqual(payload["error"], "replay_auth")


if __name__ == "__main__":
    unittest.main()
