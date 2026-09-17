# AUTH-ESCAPE-01 — Acceptance Criteria

**Status:** PRE-IMPLEMENTATION / LOCKED
**Scope:** External HTTP authorization boundary only.
**Change class:** Wire-protocol v2 breaking change.

This document defines the success conditions **before implementation**. Passing tests must not be interpreted as certification of the broader DAR gate set.

## A. Threat model and credential management

The implementation must document, before or alongside implementation:

- The exact authentication mechanism selected (for example HMAC/shared secret, bearer credential, or mTLS).
- Why that mechanism is appropriate for the stated threat model.
- The trust boundary and the attacker capabilities it is intended to address.
- What attacks the mechanism does **not** address.
- The credential/key source: environment variable, secret manager, config file, or another explicit mechanism.
- Credential storage and exposure considerations, including logs and configuration surfaces.
- Key lifecycle, rotation procedure, and whether rotation can occur without downtime.
- Behavior after credential compromise, including revocation/rotation expectations.
- If overlapping credentials are supported during rotation, how overlap is bounded and retired.
- For MAC-based authentication, the exact canonical representation covered by the MAC, algorithm, encoding, and verification rules.
- Replay protection requirements and implementation, where applicable.

"Authentication exists" is not sufficient evidence.

## B. Protected external endpoints

The same authorization boundary must protect all four external HTTP paths in the same change:

- `/fence`
- `/refuse`
- `/commit`
- `/state`

No endpoint may remain intentionally unauthenticated as an intermediate state.

## C. No authorization bypass

The authenticated HTTP path must not merely add a credential check in front of direct `PostgresAuthority` mutation. It must enforce the intended authority semantics.

Negative tests must establish that a request with otherwise valid transport credentials but **without the required verified authority/refusal intent** cannot directly obtain mutation authority for:

- `PostgresAuthority.fence()`
- `PostgresAuthority.refuse()`
- `PostgresAuthority.commit()`

The test suite must demonstrate the rejection path, not only successful authorized requests.

## D. `/state` reconnaissance boundary

`/state` must not remain an unauthenticated information-disclosure/reconnaissance path after mutation endpoints are protected.

Tests must demonstrate that an unauthenticated caller cannot obtain protected authority state through `/state`.

## E. Wire protocol v2 — breaking change

> **Wire protocol v2 is a breaking change. There is no unauthenticated backward-compatible fallback to v1.**

Requirements:

- Requests must use the explicitly documented v2 authentication contract.
- Missing, malformed, invalid, or otherwise unauthenticated credentials must be rejected.
- There must be no `missing auth -> v1` compatibility path.
- There must be no legacy endpoint or alternate parser that silently bypasses v2 authorization.
- Existing clients that do not implement v2 authentication must fail closed rather than receive unauthenticated compatibility behavior.

## F. Regression tests

The patch must add focused tests covering at minimum:

1. Unauthorized `/fence` is rejected.
2. Unauthorized `/refuse` is rejected.
3. Unauthorized `/commit` is rejected.
4. Unauthorized `/state` is rejected.
5. Malformed/missing authentication is rejected.
6. Authorized requests can execute the intended operation.
7. Valid credentials without the required verified authority/refusal intent cannot bypass the authority layer.
8. No legacy unauthenticated v1 fallback remains.

## G. Existing semantics

The patch must preserve the already-established state-level semantics unless a test explicitly documents an intentional change. AUTH-ESCAPE-01 is not permission to redesign unrelated fence, idempotency, SSL, Rekor, A9, A10, A12, or A13 behavior.

## H. Scope isolation

This implementation stage must not silently include fixes for:

- FENCE-GRIEFING-01
- commit idempotency/epoch mismatch
- SSL default/transport hardening
- A9/Rekor integration
- internal `store.py` Anchor analysis
- unrelated refactors

Those findings remain separately tracked and must be handled in their own review stages.

### Explicit scope exception — owner-approved

The `sslmode` default change in `dar_v36_14/postgres_authority.py` from `prefer` to `require` is an explicit exception to the original SSL scope-isolation exclusion.

**Approval:** The repository owner explicitly approved retaining this SSL hardening change as part of the AUTH-ESCAPE-01 patch.

**Reason for recording the exception:** The change was discovered during independent code review after implementation. It must therefore be disclosed as a scope exception rather than treated as if it had been part of the original locked scope.

The approval does not authorize any other unrelated SSL, transport, database, Rekor, A9, A10, A12, A13, fence, idempotency, or refactoring changes beyond those explicitly identified in this document.

## I. Required evidence package

The implementation must return all of the following for review:

1. Full relevant corrected code.
2. Complete wire protocol v2 specification.
3. Explicit threat model.
4. Credential/key-management design.
5. New regression tests.
6. Test execution results.
7. Exact `file:line` references for every material authorization boundary.
8. Commit SHA and branch/PR reference.
9. **Full `git diff` of the change**, showing exactly what was added, removed, and replaced, including evidence that no v1 fallback remains.

Review is performed against this document before any subsequent finding is implemented.

## Review gate

**AUTH-ESCAPE-01 is not considered accepted merely because tests pass.** The reviewer must inspect the implementation, wire protocol, threat model, negative bypass tests, and complete diff against this pre-implementation contract.
