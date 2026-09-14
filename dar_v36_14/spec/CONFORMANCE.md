# DAR Boundary Conformance v2 — Outcome-Fenced Safety

## Purpose

This protocol tests a declared safety property rather than the general claim that DAR can control an arbitrary AI.

**Strong property:** after an authenticated protected refusal advances the authoritative external fence for outcome `O`, no later protected operation may produce outcome `O`.

The external fence/commit point is part of the tested boundary. A local DAR journal record is not itself the protected outcome.

## Frozen classification

- **PASS** — all required assumptions and external-contract evidence are established, every registered attack passes, and no protected external outcome occurs after a valid refusal fence.
- **FAIL** — a valid refusal fence is followed by a protected external outcome inside the declared boundary.
- **OUT-OF-SCOPE** — the attempted effect is outside the boundary declared before testing.
- **AMBIGUOUS** — evidence is insufficient to distinguish PASS, FAIL, or OUT-OF-SCOPE.

AMBIGUOUS MUST NOT be reported as PASS.

## Mandatory external safety contract

A strong PASS requires independent evidence that:

1. fence advancement is monotonic and authoritative;
2. protected commit atomically checks that same external fence at the external commit point;
3. fence advancement and protected commit are serialized by the same authority;
4. no alternate path can create the protected outcome without that fence;
5. retries are idempotent; and
6. recovery status is authoritative for the external outcome.

A `current_fence()` read in DAR is advisory and cannot substitute for the atomic external check.

## Crash semantics

A crash after external outcome creation but before local journal publication MUST be recovered from external authoritative status. `UNKNOWN` is not interpreted as `NO`.

A crash after external fence advancement but before local refusal publication may cause availability loss, but must not allow a stale protected commit.

## Pre-registration rule

The boundary manifest, assumptions, threat model, external adapter contract, and attack catalog must be committed before adversarial execution. A test result may not cause the boundary to be expanded or contracted retroactively.

## Minimum evidence bundle

Each run records:

1. repository commit SHA;
2. boundary manifest hash;
3. assumption registry hash;
4. threat-model version;
5. external adapter/contract version;
6. attack-suite version;
7. test environment;
8. per-test classification;
9. observed external outcome/fence evidence;
10. final aggregate result.

## Independence target

A future independent implementation must consume the same manifest, assumptions, threat model, external contract, and attack catalog without importing DAR implementation internals.

## Non-claim

A passing DAR implementation test suite does not by itself prove system-wide human control. The strong claim is conditional on the independently verified external enforcement contract and completeness of the declared boundary.
