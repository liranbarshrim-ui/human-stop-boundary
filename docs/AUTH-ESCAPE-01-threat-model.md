# AUTH-ESCAPE-01 — Threat Model and Key Management

## Trust boundary

The boundary is the external HTTP server. The network caller is untrusted until transport authentication succeeds. The HTTP transport layer is not itself the decision authority: it must verify a second, operation-bound authority intent before invoking the protected authority mutation.

## Attacker capabilities

The model assumes an attacker can send arbitrary HTTP requests, omit or alter headers, alter JSON fields, replay previously observed requests, select legacy-looking payload shapes, and know endpoint names. The attacker may also possess a valid transport credential while lacking authority to authorize the requested state change.

## Addressed attacks

- Anonymous endpoint access: rejected on all four protected paths.
- Header/payload tampering: covered by transport MAC over method, path, body hash, timestamp, and nonce.
- Basic request replay: timestamp freshness plus one-use nonce cache.
- Transport credential alone causing mutation: blocked by a separate authority-intent verification step.
- Refusal-intent forgery/tampering: `/refuse` requires `RefusalAuthority.verify()` against the configured authority key.
- Legacy v1 fallback: no missing-auth compatibility branch exists.
- `/state` reconnaissance: `/state` is behind the same v2 transport authentication boundary.

## Not addressed

This stage does not claim to solve TLS configuration, host compromise, secret exfiltration from a compromised runtime, database compromise, insider misuse of an already valid authority credential, distributed nonce-cache consistency across multiple server instances, or unrelated DAR findings. Those remain outside AUTH-ESCAPE-01.

## Credential source and exposure

Transport and authority secrets are environment-provided deployment secrets: `DAR_V2_TRANSPORT_KEYS` and `DAR_V2_AUTHORITY_KEYS`. Secrets are decoded only in process memory. They must not be placed in source control, request bodies, query strings, or logs. The server intentionally does not log request headers. Deployment configuration remains a sensitive surface and must be protected by the deployment platform.

## Rotation and compromise

Keys are rotated by replacing the environment configuration and redeploying/restarting. Overlapping active credentials are not implemented. This means rotation is explicit and bounded, but zero-downtime rotation is not claimed. A compromised transport key must be removed from configuration and replaced; a compromised authority key must likewise be revoked and replaced. Fresh transport requests are limited by the configured timestamp window.

## MAC rules

Transport authentication is HMAC-SHA256 with lowercase hexadecimal output. The exact signed representation is documented in `docs/AUTH-ESCAPE-01-wire-protocol-v2.md`. Authority intent uses HMAC-SHA256 over an operation label and canonical JSON body. `/refuse` uses the existing `RefusalAuthority` canonical payload and `hmac.compare_digest` verification.

## Replay considerations

Transport requests include a unique nonce and timestamp. The server retains accepted nonces for the freshness window and rejects reuse. Because this cache is process-local, this stage does not claim replay protection across independently running replicas or after process restart. Such distributed/persistent replay protection is explicitly outside this stage.
