# AUTH-ESCAPE-01 — Wire Protocol v2

## Status

Breaking change. Wire Protocol v1 is not supported by the external HTTP server.
A request without v2 authentication fails closed; there is no parser or endpoint that treats missing authentication as v1.

## Transport authentication

Every protected request to `/state`, `/fence`, `/refuse`, and `/commit` uses these headers:

- `X-DAR-Key-Id`: identifier of a configured transport secret.
- `X-DAR-Timestamp`: Unix timestamp in seconds.
- `X-DAR-Nonce`: unique request nonce, 16–256 characters.
- `X-DAR-MAC`: lowercase hexadecimal HMAC-SHA256.

The MAC covers exactly:

`METHOD + "\n" + PATH + "\n" + SHA256(raw_request_body) + "\n" + TIMESTAMP + "\n" + NONCE`

`PATH` is the parsed URL path only. The body hash is SHA-256 over the exact bytes received. The timestamp is accepted only within `DAR_AUTH_WINDOW_SECONDS` (default 300 seconds). A nonce may be accepted once within that window. MAC comparison is constant-time.

Transport keys are loaded from `DAR_V2_TRANSPORT_KEYS` as a JSON object mapping key IDs to base64 secrets of at least 32 bytes.

## Authority authorization

Transport authentication is not mutation authority.

### `/fence` and `/commit`

The JSON body must contain `authority_intent` with:

```json
{"principal":"human-a","mac":"<hex-hmac-sha256>"}
```

The authority MAC covers exactly:

`DAR-AUTH-V2\nOPERATION\nCANONICAL_JSON_BODY_WITHOUT_authority_intent`

Canonical JSON uses sorted keys, compact separators `,` and `:`, UTF-8, and `ensure_ascii=false`.

The server resolves `principal` only against `DAR_V2_AUTHORITY_KEYS`; the matching secret must be at least 32 bytes. A valid transport credential without this verified intent is rejected before the authority mutation method is called.

### `/refuse`

The JSON body must contain `refusal_intent` with all fields required by `RefusalIntent`:
`refusal_id`, `principal`, `effect_id`, `capability_txid`, `target_epoch`, `issued_at`, `mac`, and `outcome_key`.

The intent is reconstructed as `RefusalIntent` and verified through `RefusalAuthority.verify()`. A transport credential alone cannot call `PostgresAuthority.refuse()`.

## Credential lifecycle

Secrets are supplied through environment variables and must not be committed to the repository. Rotation is performed by changing the deployed secret configuration and restarting/redeploying the service. This implementation does not provide overlapping active keys: the configured set is authoritative at process start. Therefore rotation is fail-closed and may require a deployment/restart; zero-downtime rotation is not claimed.

After compromise, immediately revoke the compromised key by removing it from the configured set and deploy the replacement. Existing signed requests remain bounded by the five-minute transport freshness window, subject to the nonce cache lifetime. Authority intents are separately signed and should be considered compromised until the corresponding authority key is rotated.

## Protected surface

`/state`, `/fence`, `/refuse`, and `/commit` all use the same transport authorization boundary. `/health` is intentionally public and exposes only service-health/protocol metadata, not authority state.

## Error behavior

Unauthenticated requests return HTTP 401 with `wire_protocol: "v2"`. Authenticated transport requests lacking verified authority intent return HTTP 403. Malformed JSON/payloads return HTTP 400. No error path invokes the protected authority mutation without the required authority/refusal verification.
