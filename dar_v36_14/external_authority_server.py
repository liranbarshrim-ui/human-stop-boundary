"""External DAR authority HTTP server, Wire Protocol v2.

AUTH-ESCAPE-01 deliberately separates transport authentication from authority
intent. A valid transport credential authenticates the caller to the HTTP
boundary; it does not itself authorize a state mutation. Mutations additionally
require a verified authority intent. There is no Wire Protocol v1 fallback.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

PERSISTENCE_MODE = os.environ.get("DAR_PERSISTENCE_MODE", "memory").strip().lower()
DB_URL = os.environ.get("DATABASE_URL", "").strip()
AUTH_WINDOW_SECONDS = int(os.environ.get("DAR_AUTH_WINDOW_SECONDS", "300"))


def _load_keys(name: str) -> dict[str, bytes]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict) or not obj:
            raise ValueError
        result = {}
        for key_id, value in obj.items():
            if not isinstance(key_id, str) or not key_id or not isinstance(value, str):
                raise ValueError
            result[key_id] = base64.b64decode(value.encode(), validate=True)
            if len(result[key_id]) < 32:
                raise ValueError
        return result
    except Exception as exc:
        raise RuntimeError(f"{name} must be a JSON object of base64 secrets (>=32 bytes)") from exc


TRANSPORT_KEYS = _load_keys("DAR_V2_TRANSPORT_KEYS")
AUTHORITY_KEYS = _load_keys("DAR_V2_AUTHORITY_KEYS")
if not TRANSPORT_KEYS or not AUTHORITY_KEYS:
    raise RuntimeError("AUTH-ESCAPE-01 requires DAR_V2_TRANSPORT_KEYS and DAR_V2_AUTHORITY_KEYS")
if AUTH_WINDOW_SECONDS <= 0:
    raise RuntimeError("DAR_AUTH_WINDOW_SECONDS must be positive")

if PERSISTENCE_MODE not in {"memory", "postgres"}:
    raise RuntimeError(f"Unsupported DAR_PERSISTENCE_MODE: {PERSISTENCE_MODE!r}")
if PERSISTENCE_MODE == "postgres" and not DB_URL:
    raise RuntimeError("DAR_PERSISTENCE_MODE=postgres requires DATABASE_URL")

if DB_URL:
    try:
        from dar_v36_14.postgres_authority import PostgresAuthority
    except ModuleNotFoundError as exc:
        if exc.name != "dar_v36_14":
            raise
        from postgres_authority import PostgresAuthority
    authority = PostgresAuthority(DB_URL)
else:
    authority = None

from dar.refusal import RefusalAuthority, RefusalIntent

BOOT_ID = uuid.uuid4().hex
lock = threading.RLock()
used_transport_nonces: dict[str, int] = {}
fences: dict[str, int] = {}
refusals: dict[str, list[object]] = {}
effects: dict[str, dict[str, object]] = {}
committed_outcomes: dict[str, str] = {}
# verify() is deliberately independent of persistence, so the same authority
# boundary is testable in memory and PostgreSQL modes.
refusal_authority = RefusalAuthority(None, AUTHORITY_KEYS)


def response(handler: BaseHTTPRequestHandler, status: int, body: dict) -> None:
    raw = json.dumps(body, sort_keys=True).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _body_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _transport_message(method: str, path: str, body_hash: str, timestamp: str, nonce: str) -> bytes:
    return "\n".join((method, path, body_hash, timestamp, nonce)).encode()


def _verify_transport(handler: BaseHTTPRequestHandler, raw: bytes) -> tuple[bool, str | None, str]:
    key_id = handler.headers.get("X-DAR-Key-Id", "")
    timestamp = handler.headers.get("X-DAR-Timestamp", "")
    nonce = handler.headers.get("X-DAR-Nonce", "")
    supplied = handler.headers.get("X-DAR-MAC", "")
    if not key_id or not timestamp or not nonce or not supplied:
        return False, None, "missing_auth"
    if key_id not in TRANSPORT_KEYS:
        return False, None, "invalid_auth"
    try:
        ts = int(timestamp)
    except ValueError:
        return False, None, "malformed_auth"
    if abs(int(time.time()) - ts) > AUTH_WINDOW_SECONDS:
        return False, None, "expired_auth"
    if len(nonce) < 16 or len(nonce) > 256:
        return False, None, "malformed_auth"
    message = _transport_message("POST" if handler.command == "POST" else "GET", urlsplit(handler.path).path, _body_hash(raw), timestamp, nonce)
    expected = hmac.new(TRANSPORT_KEYS[key_id], message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        return False, None, "invalid_auth"
    with lock:
        now = int(time.time())
        for old_nonce, seen_at in list(used_transport_nonces.items()):
            if now - seen_at > AUTH_WINDOW_SECONDS:
                used_transport_nonces.pop(old_nonce, None)
        if nonce in used_transport_nonces:
            return False, None, "replay_auth"
        used_transport_nonces[nonce] = now
    return True, key_id, "ok"


def _authority_message(operation: str, body: dict) -> bytes:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"DAR-AUTH-V2\n{operation}\n{canonical}".encode()


def _verify_authority_intent(operation: str, body: dict) -> bool:
    intent = body.get("authority_intent")
    if not isinstance(intent, dict):
        return False
    principal = intent.get("principal")
    mac = intent.get("mac")
    if not isinstance(principal, str) or not isinstance(mac, str):
        return False
    credential = AUTHORITY_KEYS.get(principal)
    if credential is None:
        return False
    signed_body = dict(body)
    signed_body.pop("authority_intent", None)
    expected = hmac.new(credential, _authority_message(operation, signed_body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)


def _refusal_from_body(body: dict) -> RefusalIntent | None:
    intent = body.get("refusal_intent")
    if not isinstance(intent, dict):
        return None
    required = ("refusal_id", "principal", "effect_id", "capability_txid", "target_epoch", "issued_at", "mac", "outcome_key")
    if any(k not in intent for k in required):
        return None
    try:
        return RefusalIntent(
            str(intent["refusal_id"]), str(intent["principal"]), str(intent["effect_id"]),
            str(intent["capability_txid"]), int(intent["target_epoch"]), int(intent["issued_at"]),
            str(intent["mac"]), str(intent["outcome_key"]),
        )
    except (TypeError, ValueError):
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        pass

    def _auth(self, raw: bytes) -> bool:
        ok, _key_id, error = _verify_transport(self, raw)
        if not ok:
            response(self, 401, {"ok": False, "error": error, "wire_protocol": "v2"})
        return ok

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/state":
            if not self._auth(b""):
                return
            if authority:
                try:
                    body = authority.state()
                    body["boot_id"] = BOOT_ID
                    return response(self, 200, body)
                except Exception as exc:
                    return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})
            with lock:
                return response(self, 200, {
                    "fences": dict(fences), "refusals": dict(refusals), "effects": dict(effects),
                    "committed_outcomes": dict(committed_outcomes), "boot_id": BOOT_ID,
                })
        if path == "/health":
            return response(self, 200, {"ok": True, "wire_protocol": "v2", "boot_id": BOOT_ID})
        return response(self, 404, {"error": "not_found", "wire_protocol": "v2"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return response(self, 400, {"ok": False, "error": "malformed_request"})
        raw = self.rfile.read(length)
        if not self._auth(raw):
            return
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return response(self, 400, {"ok": False, "error": "malformed_json", "wire_protocol": "v2"})
        if not isinstance(data, dict):
            return response(self, 400, {"ok": False, "error": "malformed_json", "wire_protocol": "v2"})

        operation = path.lstrip("/")
        if operation not in {"fence", "refuse", "commit"}:
            return response(self, 404, {"error": "not_found", "wire_protocol": "v2"})

        if operation == "refuse":
            refusal = _refusal_from_body(data)
            if refusal is None or not refusal_authority.verify(refusal):
                return response(self, 403, {"ok": False, "error": "authority_intent_required", "wire_protocol": "v2"})
            data = {"outcome": refusal.outcome_key, "epoch": refusal.target_epoch, "refusal_id": refusal.refusal_id}
        elif not _verify_authority_intent(operation, data):
            return response(self, 403, {"ok": False, "error": "authority_intent_required", "wire_protocol": "v2"})

        if authority:
            try:
                if operation == "fence":
                    status, body = authority.fence(data["outcome"], int(data["epoch"]))
                elif operation == "refuse":
                    status, body = authority.refuse(data["outcome"], int(data["epoch"]), data["refusal_id"])
                else:
                    status, body = authority.commit(data["outcome"], int(data["epoch"]), data["idempotency_key"])
                return response(self, status, body)
            except (KeyError, TypeError, ValueError) as exc:
                return response(self, 400, {"ok": False, "error": "invalid_v2_payload", "detail": str(exc)})
            except Exception as exc:
                return response(self, 503, {"ok": False, "error": "database_unavailable", "detail": str(exc)})

        with lock:
            try:
                if operation == "fence":
                    outcome = data["outcome"]; epoch = int(data["epoch"])
                    if epoch < fences.get(outcome, 0): return response(self, 409, {"ok": False, "error": "fence_rollback"})
                    if outcome in refusals: return response(self, 409, {"ok": False, "error": "terminal_refusal"})
                    fences[outcome] = epoch
                    return response(self, 200, {"ok": True})
                if operation == "refuse":
                    outcome = data["outcome"]; epoch = int(data["epoch"]); refusal_id = data["refusal_id"]
                    existing = refusals.get(outcome)
                    if existing is not None:
                        same = existing == [epoch, refusal_id]
                        return response(self, 200, {"ok": same, "idempotent": same})
                    if epoch < fences.get(outcome, 0): return response(self, 409, {"ok": False, "error": "fence_rollback"})
                    fences[outcome] = epoch; refusals[outcome] = [epoch, refusal_id]
                    return response(self, 200, {"ok": True, "idempotent": False})
                outcome = data["outcome"]; epoch = int(data["epoch"]); idem = data["idempotency_key"]
                if outcome in refusals: return response(self, 409, {"ok": False, "error": "terminal_refusal"})
                if fences.get(outcome, 0) != epoch: return response(self, 409, {"ok": False, "error": "stale_fence"})
                if idem in effects: return response(self, 200, {"ok": True, "idempotent": True})
                if outcome in committed_outcomes: return response(self, 409, {"ok": False, "error": "outcome_already_committed"})
                effects[idem] = {"outcome": outcome, "epoch": epoch}; committed_outcomes[outcome] = idem
                return response(self, 200, {"ok": True, "idempotent": False})
            except (KeyError, TypeError, ValueError) as exc:
                return response(self, 400, {"ok": False, "error": "invalid_v2_payload", "detail": str(exc)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
