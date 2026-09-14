# DAR v37 — External Conformance Gate

## Purpose

DAR v37 is an evidence gate, not a new safety claim. It raises the burden from a successful external 250-round black-box run to a repeatable stress protocol and makes the remaining environmental prerequisites explicit.

## Gate A — external black-box stress

The reference deployment is tested without importing its internal implementation:

- 10,000 concurrent refusal/commit races;
- 32 workers;
- PostgreSQL-backed persistence;
- every round must complete;
- no round may produce both a refusal winner and a protected commit winner;
- a fresh idempotency key must not bypass a terminal refusal;
- a protected commit that legitimately wins must remain committed against a later refusal;
- machine-readable evidence must end in `verdict: PASS`.

The workflow is manual by design so routine pushes do not repeatedly impose a high external load on the hosted research service.

## Gate B — crash/restart matrix

A conforming deployment must provide evidence for:

1. refusal before local persistence;
2. protected commit before local persistence;
3. refusal/commit race;
4. retry with a new idempotency key after refusal;
5. interrupted PostgreSQL transaction and rollback;
6. real deployment restart followed by refusal-state verification;
7. recovery/reconciliation of pending intents under the declared adapter contract.

## Gate C — environment, not implementation

A DAR implementation cannot certify its own external monotonic anchor or interface completeness. A v2 PASS requires both conditions from the preregistered boundary manifest:

- an external monotonic anchor outside the rollback domain;
- an independent interface-completeness / escape audit covering every process, IPC path, adapter, helper, filesystem path, and alternate route capable of producing the protected effect.

Missing evidence is `AMBIGUOUS` or `OUT-OF-SCOPE`, never PASS.

## Gate D — second-provider reproduction

A second independently administered infrastructure deployment is required before a cross-provider conformance claim. The second deployment must be operationally independent and its evidence must be generated from the same frozen protocol, not from a provider-specific implementation shortcut.

## Final claim boundary

Even if all gates pass, the resulting claim remains conditional on the registered protected-effect boundary. It does **not** establish universal control over arbitrary AI systems, universal complete mediation, or safety outside the declared boundary.

## Current status

- Reference Render black-box: 250/250 PASS, PostgreSQL persistence, 16 workers.
- Crash-boundary suite: PASS for the five registered scenarios.
- Second-provider reproduction: **PENDING**.
- Independent interface-completeness audit: **PENDING**.
- External monotonic-anchor validation: **PENDING**.
- 10,000-round stress run: **PENDING execution**.

No DAR v2/core-property PASS should be reported until the pending gates are independently evidenced.
