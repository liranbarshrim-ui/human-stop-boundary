# AUTH-ESCAPE-01 — Wire Protocol v2

## Breaking-change rule

> Wire protocol v2 is a breaking change. There is no unauthenticated backward-compatible fallback to v1.

Old clients that do not send valid v2 authentication fail closed.

## Transport authentication

Every protected request carries:

```text
X-DAR-Principal: <principal>
X-DAR-Timestamp: <unix-seconds>
X-DAR-Nonce: <fresh-random-value>
X-DAR-Signature: <hex HMAC-SHA256>
```

The transport MAC is computed over:

```text
METHOD|PATH|TIMESTAMP|NONCE|SHA256(EXACT_BODY_BYTES)
```

The server verifies the principal credential, timestamp freshness, nonce freshness, and MAC before executing the protected operation.

## Authority intent

Mutation endpoints additionally require a JSON `authority_intent` object:

```json
{
  "principal": "<principal>",
  "operation": "fence|refuse|commit",
  "outcome": "<outcome>",
  "epoch": 1,
  "refusal_id": "<refusal-id-or-empty>",
  "idempotency_key": "<key-or-empty>",
  "issued_at": 0,
  "nonce": "<fresh-random-value>",
  "mac": "<hex HMAC-SHA256>"
}
```

The intent MAC is computed over the fields in this exact order:

```text
principal|operation|outcome|epoch|refusal_id|idempotency_key|issued_at|nonce
```

The intent credential set is distinct from the transport credential set. A valid transport credential without a valid authority intent cannot mutate the authority.

### Single-use intent and retry semantics

An `authority_intent` is a **single-use authorization envelope**.

The intent nonce is consumed after the server successfully verifies the intent MAC, principal binding, operation binding, and freshness, **before** the protected authority operation is attempted.

Therefore:

- A successful operation consumes the intent.
- A business-level rejection such as `409 stale_fence` also consumes the intent.
- An infrastructure failure such as `503 database_unavailable` also consumes the intent.
- Reusing the same intent nonce is rejected as `intent_replay_detected`, even if the first attempt did not complete the requested operation.
- Clients **MUST issue a fresh `authority_intent` with a fresh intent nonce for every retry attempt**. A client MUST NOT resend the same signed intent JSON after any failed or rejected attempt.

This is intentional: an authority intent authorizes one execution attempt, not an unlimited number of retries.

## Endpoint rules

| Endpoint | Protection | v1 fallback |
|---|---|---|
| `GET /health` | Public | N/A |
| `GET /` | Public | N/A |
| `GET /state` | Transport authentication | None |
| `POST /fence` | Transport + authority intent | None |
| `POST /refuse` | Transport + authority intent | None |
| `POST /commit` | Transport + authority intent | None |

## Failure behavior

Missing, malformed, expired, unknown-principal, invalid-MAC, replayed transport authentication, missing intent, expired intent, invalid intent, or replayed intent causes rejection before the protected authority mutation is executed.
