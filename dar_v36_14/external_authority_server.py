"""External DAR authority, wire protocol v2.

Protected endpoints require two distinct proofs:
1. transport authentication (principal/timestamp/nonce/HMAC), and
2. a signed authority-intent envelope bound to the requested operation.

Wire protocol v2 is a breaking change. There is no unauthenticated
backward-compatible fallback to v1.
"""
from __future__ import annotations

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
AUTH_CREDENTIALS_JSON = os.environ.get("DAR_AUTH_CREDENTIALS_JSON", "{}").strip()
INTENT_CREDENTIALS_JSON = os.environ.get("DAR_INTENT_CREDENTIALS_JSON", "{}").strip()
AUTH_MAX_SKEW = int(os.environ.get("DAR_AUTH_MAX_SKEW_SECONDS", "300"))

if PERSISTENCE_MODE not in {"memory", "postgres"}:
    raise RuntimeError(f"Unsupported DAR_PERSISTENCE_MODE: {PERSISTENCE_MODE!r}")
if PERSISTENCE_MODE == "postgres" and not DB_URL:
    raise RuntimeError("DAR_PERSISTENCE_MODE=postgres requires DATABASE_URL")


def _load_credentials(raw: str, name: str) -> dict[str, str]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must be valid JSON") from exc
    if not isinstance(value, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) or not v
        for k, v in value.items()
    ):
        raise RuntimeError(
            f"{name} must be a JSON object mapping principal to non-empty secret"
        )
    return value


AUTH_CREDENTIALS = _load_credentials(AUTH_CREDENTIALS_JSON, "DAR_AUTH_CREDENTIALS_JSON")
INTENT_CREDENTIALS = _load_credentials(
    INTENT_CREDENTIALS_JSON, "DAR_INTENT_CREDENTIALS_JSON"
)

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

BOOT_ID = uuid.uuid4().hex
lock = threading.RLock()
replay_nonces: dict[str, float] = {}
fences: dict[str, int] = {}
refusals: dict[str, list[object]] = {}
effects: dict[str, dict[str, object]] = {}
committed_outcomes: dict[str, str] = {}


def response(handler: BaseHTTPRequestHandler, status: int, body: dict) -> None:
    raw = json.dumps(body, sort_keys=True).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _canonical_transport(
    method: str, path: str, timestamp: str, nonce: str, body: bytes
) -> bytes:
    digest = hashlib.sha256(body).hexdigest()
    return "|".join((method.upper(), path, timestamp, nonce, digest)).encode()


def _verify_transport(
    handler: BaseHTTPRequestHandler, path: str, body: bytes
) -> tuple[str | None, str | None]:
    principal = handler.headers.get("X-DAR-Principal")
    timestamp = handler.headers.get("X-DAR-Timestamp")
    nonce = handler.headers.get("X-DAR-Nonce")
    signature = handler.headers.get("X-DAR-Signature")
    if not principal or not timestamp or not nonce or not signature:
        return None, "missing_auth"
    secret = AUTH_CREDENTIALS.get(principal)
    if secret is None:
        return None, "invalid_auth"
    try:
        ts = int(timestamp)
    except ValueError:
        return None, "invalid_auth"
    if abs(int(time.time()) - ts) > AUTH_MAX_SKEW:
        return None, "auth_expired"
    if len(nonce) < 16 or len(signature) != 64:
        return None, "invalid_auth"
    method = "POST" if handler.command == "POST" else "GET"
    canonical = _canonical_transport(method, path, timestamp, nonce, body)
    expected = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None, "invalid_auth"
    with lock:
        now = time.time()
        stale = [key for key, expires in replay_nonces.items() if expires <= now]
        for key in stale:
            replay_nonces.pop(key, None)
        if nonce in replay_nonces:
            return None, "replay_detected"
        replay_nonces[nonce] = now + AUTH_MAX_SKEW
    return principal, None


def _verify_intent(
    handler: BaseHTTPRequestHandler,
    path: str,
    data: dict,
    principal: str,
) -> str | None:
    raw = data.get("authority_intent")
    if not isinstance(raw, dict):
        return "missing_authority_intent"
    intent_principal = raw.get("principal")
    operation = raw.get("operation")
    outcome = raw.get("outcome")
    epoch = raw.get("epoch")
    issued_at = raw.get("issued_at")
    intent_nonce = raw.get("nonce")
    intent_mac = raw.get("mac")
    if intent_principal != principal or operation != path.lstrip("/"):
        return "invalid_authority_intent"
    if not isinstance(outcome, str) or not outcome or not isinstance(epoch, int):
        return "invalid_authority_intent"
    if not isinstance(issued_at, int) or abs(int(time.time()) - issued_at) > AUTH_MAX_SKEW:
        return "expired_authority_intent"
    if not isinstance(intent_nonce, str) or len(intent_nonce) < 16 or not isinstance(intent_mac, str):
        return "invalid_authority_intent"
    secret = INTENT_CREDENTIALS.get(principal)
    if secret is None:
        return "invalid_authority_intent"
    refusal_id = raw.get("refusal_id", "")
    idempotency_key = raw.get("idempotency_key", "")
    canonical = "|".join(
        (
            principal,
            operation,
            outcome,
            str(epoch),
            str(refusal_id),
            str(idempotency_key),
            str(issued_at),
            intent_nonce,
        )
    ).encode()
    expected = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, intent_mac):
        return "invalid_authority_intent"
    return None


def _protected(
    handler: BaseHTTPRequestHandler, path: str, body: bytes, data: dict
) -> tuple[str | None, str | None]:
    principal, error = _verify_transport(handler, path, body)
    if error:
        return None, error
    intent_error = _verify_intent(handler, path, data, principal or "")
    if intent_error:
        return None, intent_error
    return principal, None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        pass

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            if authority:
                try:
                    authority.health()
                except Exception as exc:
                    return response(
                        self,
                        503,
                        {"ok": False, "error": "database_unavailable", "detail": str(exc)},
                    )
            return response(
                self,
                200,
                {
                    "ok": True,
                    "persistence": "postgres" if authority else "memory",
                    "boot_id": BOOT_ID,
                    "wire_protocol": "v2",
                },
            )
        if path == "/state":
            _, error = _verify_transport(self, path, b"")
            if error:
                return response(self, 401, {"ok": False, "error": error})
            if authority:
                try:
                    state = authority.state()
                    state["boot_id"] = BOOT_ID
                    return response(self, 200, state)
                except Exception as exc:
                    return response(
                        self,
                        503,
                        {"ok": False, "error": "database_unavailable", "detail": str(exc)},
                    )
            with lock:
                return response(
                    self,
                    200,
                    {
                        "fences": dict(fences),
                        "refusals": dict(refusals),
                        "effects": dict(effects),
                        "committed_outcomes": dict(committed_outcomes),
                        "boot_id": BOOT_ID,
                    },
                )
        if path == "/":
            return response(
                self,
                200,
                {
                    "service": "DAR external authority",
                    "health": "/health",
                    "wire_protocol": "v2",
                    "boot_id": BOOT_ID,
                },
            )
        return response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return response(self, 400, {"ok": False, "error": "invalid_content_length"})
        body = self.rfile.read(length)
        try:
            data = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return response(self, 400, {"ok": False, "error": "invalid_json"})
        if not isinstance(data, dict):
            return response(self, 400, {"ok": False, "error": "invalid_json"})
        if path not in {"/fence", "/refuse", "/commit"}:
            return response(self, 404, {"error": "not_found"})

        principal, auth_error = _protected(self, path, body, data)
        if auth_error:
            status = 409 if auth_error == "replay_detected" else 401
            return response(self, status, {"ok": False, "error": auth_error})
        _ = principal

        if authority:
            try:
                if path == "/fence":
                    status, result = authority.fence(data["outcome"], int(data["epoch"]))
                    return response(self, status, result)
                if path == "/refuse":
                    status, result = authority.refuse(
                        data["outcome"], int(data["epoch"]), data["refusal_id"]
                    )
                    return response(self, status, result)
                if path == "/commit":
                    status, result = authority.commit(
                        data["outcome"], int(data["epoch"]), data["idempotency_key"]
                    )
                    return response(self, status, result)
            except (KeyError, TypeError, ValueError):
                return response(self, 400, {"ok": False, "error": "invalid_request"})
            except Exception as exc:
                return response(
                    self,
                    503,
                    {"ok": False, "error": "database_unavailable", "detail": str(exc)},
                )

        with lock:
            try:
                outcome = data["outcome"]
                epoch = int(data["epoch"])
            except (KeyError, TypeError, ValueError):
                return response(self, 400, {"ok": False, "error": "invalid_request"})
            if path == "/fence":
                if epoch < fences.get(outcome, 0):
                    return response(self, 409, {"ok": False, "error": "fence_rollback"})
                if outcome in refusals:
                    return response(self, 409, {"ok": False, "error": "terminal_refusal"})
                fences[outcome] = epoch
                return response(self, 200, {"ok": True})
            if path == "/refuse":
                refusal_id = data.get("refusal_id")
                existing = refusals.get(outcome)
                if existing is not None:
                    same = existing == [epoch, refusal_id]
                    return response(self, 200, {"ok": same, "idempotent": same})
                if epoch < fences.get(outcome, 0):
                    return response(self, 409, {"ok": False, "error": "fence_rollback"})
                fences[outcome] = epoch
                refusals[outcome] = [epoch, refusal_id]
                return response(self, 200, {"ok": True, "idempotent": False})
            idem = data.get("idempotency_key")
            if outcome in refusals:
                return response(self, 409, {"ok": False, "error": "terminal_refusal"})
            if fences.get(outcome, 0) != epoch:
                return response(self, 409, {"ok": False, "error": "stale_fence"})
            if idem in effects:
                existing = effects[idem]
                if existing["outcome"] != outcome or existing["epoch"] != epoch:
                    return response(self, 409, {"ok": False, "error": "idempotency_mismatch"})
                return response(self, 200, {"ok": True, "idempotent": True})
            if outcome in committed_outcomes:
                return response(self, 409, {"ok": False, "error": "outcome_already_committed"})
            effects[idem] = {"outcome": outcome, "epoch": epoch}
            committed_outcomes[outcome] = idem
            return response(self, 200, {"ok": True, "idempotent": False})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
