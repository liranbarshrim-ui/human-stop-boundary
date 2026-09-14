# DAR Boundary Conformance — Empirical Attack Status v3

Status: **PRE-REGISTERED / PENDING REQUIRED EVIDENCE**

The repository now contains an executable reference model for the external atomic-fence contract. This strengthens the attack suite, but it does **not** substitute for deployment-specific evidence about a real external system.

| Condition | Required evidence | Current status |
|---|---|---|
| External monotonic anchor (A9) | deployment-specific anchor plus rollback restoration test | **PENDING** |
| Interface completeness (A1/A11) | independent interface/escape audit covering all protected-effect paths | **PENDING** |
| External fence/commit atomicity (A10) | independent transaction/adapter audit plus adversarial race test on the real authority | **PENDING** |
| Protected outcome idempotency (A12) | real retry/crash/replay evidence | **PENDING** |
| Registered-path attack probes A-01–A-12 | executable test suite, including atomic-fence reference model | **BOUNDED EVIDENCE** |

## New executable evidence

`tests/test_atomic_fence_authority_v1.py` models a single authoritative serialization domain in which fence advancement and external commit share one lock. It tests:

- refusal wins before a stale commit;
- a commit that wins before refusal remains a real outcome (no retroactive `NO`);
- crash after external commit is `UNKNOWN` to the caller but `COMMITTED` to authoritative status;
- repeated accepted commits are idempotent;
- an adversarial fence change at the commit point prevents the protected effect.

This model demonstrates the **shape** of the required external contract. It is not proof that a production adapter has that contract.

## Interpretation

The existing A-05 test demonstrates rejection of a Store state below a supplied anchor. It does **not** prove that every deployment has such an anchor. A deployment without an external anchor must not receive PASS for anti-rollback.

The path and race tests provide deployment-bounded evidence for the tested code paths. They do **not** constitute an independent completeness audit, and a DAR-side advisory fence read cannot establish external atomicity.

A crash in which the external system may already have committed the outcome must never be classified as `NO`. `UNKNOWN` remains `UNKNOWN` until authoritative external status resolves it.

## Required next validation

1. Freeze a concrete deployment and external anchor implementation.
2. Independently enumerate every path capable of producing the protected outcome.
3. Independently verify that fence advancement and protected commit serialize at the same authoritative commit point.
4. Run rollback, crash, retry, and race attacks against the frozen deployment.
5. Verify idempotency and authoritative status on the real external system.
6. Preserve independent evidence separately from DAR-authored tests.
7. Only then classify the strong outcome property as PASS, FAIL, or AMBIGUOUS under the frozen rules.

Until these steps are complete, the repository's defensible claim is **conditional protected-outcome enforcement under a specified external contract**, not demonstrated system-wide human control.
