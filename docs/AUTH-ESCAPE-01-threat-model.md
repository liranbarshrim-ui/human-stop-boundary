# AUTH-ESCAPE-01 — Threat Model

Status: IMPLEMENTED ON `auth-escape-01-patch`; verification remains STOP until the evidence workflow is reviewed and independently executed.

## Protected boundary

The external HTTP authority exposes four protected endpoints:

- `POST /fence`
- `POST /refuse`
- `POST /commit`
- `GET /state`

`GET /health` and `GET /` remain public and contain no authoritative state.

## Authentication mechanism

Wire protocol v2 uses HMAC-SHA256 transport authentication with:

- `X-DAR-Principal`
- `X-DAR-Timestamp`
- `X-DAR-Nonce`
- `X-DAR-Signature`

The signature covers the HTTP method, path, timestamp, nonce, and SHA-256 digest of the exact request body. Missing, malformed, expired, unknown-principal, or invalid signatures are rejected. Nonces are rejected on reuse during the configured timestamp window.

A second HMAC-SHA256 proof, `authority_intent`, is required for mutation endpoints. Its credential set is separate from the transport credential set. The intent binds the principal, operation, outcome, epoch, refusal ID, idempotency key, issuance time, and intent nonce.

## Credential source and handling

Credentials are supplied through environment variables:

- `DAR_AUTH_CREDENTIALS_JSON`
- `DAR_INTENT_CREDENTIALS_JSON`

The application does not write these credentials to response bodies or test artifacts. Production deployment must supply them through the platform secret mechanism rather than committing them to source control.

Rotation currently requires replacing the configured credential set and restarting/redeploying the service. There is no zero-downtime overlap protocol in v2.

## Trust boundary and attacker capabilities

The protected HTTP listener is treated as hostile at its network boundary. An attacker may send arbitrary HTTP requests, alter request bodies, replay previously observed requests, omit or corrupt authentication headers, use an unknown principal, or possess a transport credential without the separate authority-intent credential.

The design does not claim to protect against compromise of the host process, arbitrary code execution on the server, compromise of the secret-management platform, or an operator who can replace the deployed application and its secrets.

## Authorization and bypass requirement

Transport authentication is not sufficient for mutation. A valid transport credential without a valid operation-bound `authority_intent` is rejected before `PostgresAuthority` or the in-memory mutation path is reached.

There is no unauthenticated compatibility path to v1.

## Replay protection

Transport requests require a fresh timestamp and nonce. Reuse of a nonce within the accepted timestamp window is rejected. Authority intents also contain their own nonce and timestamp and are MAC-bound to the operation and request parameters.

The current nonce cache is process-local. It is therefore not a claim of cross-restart replay resistance; deployment-level persistence of replay state is a separate hardening concern.

## Security limitations

HMAC provides authentication and integrity only when the credential remains secret. It does not provide non-repudiation. TLS remains required for production transport. The external authority still depends on the underlying `PostgresAuthority` semantics for fence, refusal, commit, and idempotency behavior; AUTH-ESCAPE-01 does not redesign those semantics.
