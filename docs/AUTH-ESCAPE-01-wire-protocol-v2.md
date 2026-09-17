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

Missing, malformed, expired, unknown-principal, invalid-MAC, replayed transport authentication, missing intent, expired intent, or invalid intent causes rejection before the protected authority mutation is executed.
