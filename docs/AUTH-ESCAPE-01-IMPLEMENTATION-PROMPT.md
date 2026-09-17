# AUTH-ESCAPE-01 — Implementation Lock

## Scope lock
Implement **only** AUTH-ESCAPE-01, the external HTTP authorization boundary.

Do not implement or modify FENCE-GRIEFING-01, commit idempotency/epoch mismatch, SSL hardening, A9/Rekor, internal store Anchor analysis, or unrelated refactors.

## Required work
1. Document the explicit authentication mechanism and threat model.
2. Define credential/key source, storage/exposure, lifecycle, rotation, compromise and replay behavior.
3. Implement Wire Protocol v2 as a breaking change with no unauthenticated v1 fallback.
4. Protect `/fence`, `/refuse`, `/commit`, and `/state` with the same authorization boundary.
5. Ensure valid transport credentials alone cannot obtain mutation authority without the required verified authority/refusal intent.
6. Add negative no-bypass tests specifically demonstrating rejection against direct authority-layer mutation paths, including the `RefusalAuthority.verify()` boundary where applicable.
7. Add regression tests for unauthorized `/fence`, `/refuse`, `/commit`, `/state`, malformed/missing auth, authorized operation, no-bypass, and absence of v1 fallback.
8. Return the complete evidence package: corrected code, wire protocol v2 spec, threat model, credential design, tests, execution results, exact file:line references, commit SHA/branch/PR, and full git diff.

## Pre-code confirmation required
Before writing or changing code, respond exactly with an explicit confirmation that the implementation will cover:

> I will implement authentication on /fence, /refuse, /commit, /state, including the threat model, Wire Protocol v2, and a no-bypass test against the RefusalAuthority verification/authority boundary. I confirm this is the only scope for AUTH-ESCAPE-01.

Do not claim PASS or completion from unrelated A9/A13/restart/10K evidence.
