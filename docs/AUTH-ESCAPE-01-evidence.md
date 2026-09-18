# AUTH-ESCAPE-01 — Review Evidence Package

## 1. Full relevant corrected code

Primary implementation: `dar_v36_14/external_authority_server.py`.
The patch replaces the unauthenticated external HTTP boundary with Wire Protocol v2 transport authentication and a second authority-intent gate. No unrelated DAR subsystem was modified.

## 2. Complete Wire Protocol v2 specification

See `docs/AUTH-ESCAPE-01-wire-protocol-v2.md`.

The transport MAC is HMAC-SHA256 over the exact method/path/body-hash/timestamp/nonce representation. Protected endpoints are `/state`, `/fence`, `/refuse`, and `/commit`. Missing authentication is rejected; there is no v1 fallback.

## 3. Explicit threat model

See `docs/AUTH-ESCAPE-01-threat-model.md`.

The attacker model includes arbitrary HTTP callers, payload/header tampering, replay, legacy-looking requests, and callers who possess transport credentials but lack mutation authority. The model explicitly records attacks not addressed by this stage.

## 4. Credential/key-management design

- Transport secrets: `DAR_V2_TRANSPORT_KEYS`.
- Authority secrets: `DAR_V2_AUTHORITY_KEYS`.
- Format: JSON object mapping key IDs/principals to base64 secrets; each secret must decode to at least 32 bytes.
- Secrets are deployment configuration, never source-controlled.
- Rotation is replacement + redeploy/restart; overlapping active keys and zero-downtime rotation are not claimed.
- Compromise requires immediate revocation/replacement.
- Transport freshness defaults to 300 seconds and uses a one-use nonce cache.

`render.yaml` declares both secret variables with `sync: false`, so their values are supplied by the deployment operator rather than committed.

## 5. New regression tests

`dar_v36_14/tests/test_auth_escape_01.py` covers:

1. unauthenticated `/fence`, `/refuse`, `/commit`, `/state`;
2. missing/tampered authentication;
3. transport credentials without authority intent for all mutation endpoints;
4. successful v2 fence/commit/refuse/state operations;
5. direct `RefusalAuthority.verify()` boundary through `/refuse` and tamper rejection;
6. no legacy v1 fallback;
7. transport replay rejection.

## 6. Test execution results

GitHub Actions run **DAR CI #434** executed the corrected branch. On Python 3.12 and 3.11, the focused AUTH-ESCAPE-01 tests passed; the full portable suite reported **95 passed, 1 failed**. The sole failure is the pre-existing conformance assertion `test_br_b3_strong_outcome_fence_is_pre_registered`, where the repository's existing `boundary_manifest_v3.json` has status `frozen-evidence-package` rather than `pre-registered`. That failure is outside AUTH-ESCAPE-01 and was not changed.

The earlier run before the fixture correction had three AUTH-ESCAPE-01 test failures; those were corrected. The subsequent run shows the AUTH-ESCAPE-01 test failures eliminated and only the unrelated conformance failure remains.

## 7. Material authorization-boundary references

References are to the current `dar_v36_14/external_authority_server.py` on branch `auth-escape-01`:

- `26-43`: `_load_keys()` validates deployment secrets and minimum key length.
- `46-54`: required v2 credential configuration and persistence preconditions.
- `93-123`: `_verify_transport()` checks required headers, key ID, timestamp freshness, MAC, and nonce replay.
- `134-151`: `_authority_message()` and `_verify_authority_intent()` provide the second authorization layer for `/fence` and `/commit`.
- `154-171`: `_refusal_from_body()` reconstructs the signed refusal intent.
- `178-182`: `_auth()` is the common HTTP transport gate.
- `185-204`: `/state` is explicitly behind `_auth()`; `/health` is the only public health endpoint.
- `206-230`: POST parsing and operation dispatch require verified authority intent before the protected authority call.
- `213-218`: `/refuse` calls `RefusalAuthority.verify()` before `PostgresAuthority.refuse()`.
- `219-222`: `/fence` and `/commit` require `_verify_authority_intent()` before mutation.

The existing internal authority verification boundary is in `dar_v36_14/dar/refusal.py`, `RefusalAuthority.verify()`, and is unchanged by this stage.

## 8. Commit SHA and branch/PR

Branch: `auth-escape-01`

The current head is the commit containing this evidence package. The implementation commit immediately before the evidence package is `0438cfa27f1a228cd85fff958f05f3c83f3bd9b8`.

Pull request: #10 — `AUTH-ESCAPE-01: Wire Protocol v2 authorization boundary`

The PR targets `main` and is intentionally left open for review; it is not merged and this evidence does not claim acceptance or certification.

## 9. Full git diff

The complete unified diff for PR #10 is the authoritative review artifact. At the implementation commit it contained exactly five changed files:

- `dar_v36_14/external_authority_server.py`
- `dar_v36_14/tests/test_auth_escape_01.py`
- `docs/AUTH-ESCAPE-01-threat-model.md`
- `docs/AUTH-ESCAPE-01-wire-protocol-v2.md`
- `render.yaml`

This evidence file was added afterward, so the current PR contains six changed files including this evidence package. The implementation diff shows the old unauthenticated endpoint handling removed and the v2 gates inserted. There is no branch in the implementation that treats missing authentication as v1. The `health` endpoint remains public by explicit design and does not expose authority state.

## Scope isolation statement

This package addresses only AUTH-ESCAPE-01. It does not implement or modify FENCE-GRIEFING-01, commit idempotency/epoch mismatch, SSL hardening, A9/Rekor integration, internal `store.py` Anchor analysis, or unrelated refactors.

## Review status

**Implementation complete for review; AUTH-ESCAPE-01 acceptance remains a reviewer decision.** Passing tests are not treated as certification of the broader DAR gate set.
