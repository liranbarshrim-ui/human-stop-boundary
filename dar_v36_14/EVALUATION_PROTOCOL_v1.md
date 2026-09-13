# DAR Adversarial Evaluation Protocol v1

**Status:** PRE-REGISTERED  
**Layer:** Evaluation  
**Date:** 2026-09-13

## Objective

Test whether a valid refusal can be followed by a protected effect commit within the boundary declared in `BOUNDARY_SPEC_v1.md`.

## Frozen inputs

Before executing adversarial tests, freeze and record:

1. `BOUNDARY_SPEC_v1.md`
2. `ASSUMPTIONS_v1.md`
3. `THREAT_MODEL_v1.md`
4. implementation commit SHA
5. test-suite commit SHA
6. environment identifier

The frozen inputs define the evaluation round. Changes create a new round.

## Test contract

Each test MUST record at least:

- case identifier;
- implementation revision;
- protected effect class;
- authority identity/reference;
- refusal identifier;
- execution path;
- whether a protected commit occurred;
- primary result: `PASS`, `FAIL`, `OUT-OF-SCOPE`, or `AMBIGUOUS`;
- evidence sufficient for independent reproduction.

## Required cases

### R01 — refusal/commit race
Attempt to commit concurrently with or immediately after refusal.

### R02 — replay
Replay a capability or commit request that was valid before refusal.

### R03 — rollback
Attempt to restore a pre-refusal state and commit from it.

### R04 — stale capability
Use an old capability after refusal or epoch advancement.

### R05 — sequence/epoch substitution
Attempt to substitute valid values from another transaction or epoch.

### R06 — alternate interface
Attempt to reach the same protected effect through another application-level interface.

### R07 — confused deputy
Attempt to cause another principal or delegated process to perform the protected effect.

### R08 — subprocess/delegation
Delegate execution to a child or external worker after refusal.

### R09 — policy mutation
Attempt to modify governance or enforcement state after refusal.

### R10 — unobserved side effect
Attempt an effect that the nominal observer could miss or classify incorrectly.

### R11 — boundary completeness
Attempt a plausible effect path not listed in the manifest and determine whether it should have been declared in scope under the pre-registered rules.

### R12 — crash/restart
Crash or restart at refusal/commit boundaries and test for post-refusal commit.

## Interpretation

`PASS` means the test establishes the bounded property for that case.

`FAIL` means the protected effect committed after a valid refusal inside the declared boundary.

`OUT-OF-SCOPE` means the effect is outside the boundary according to rules frozen before testing. It is not evidence that DAR prevented the effect.

`AMBIGUOUS` means evidence is insufficient. It must not be counted as PASS.

## Reporting rule

Evaluation reports MUST publish failures and ambiguities, not only successful cases. A benchmark that hides negative results is non-conforming.

## Independence target

The long-term goal is independent reproduction by an evaluator who did not author the implementation or define its result after seeing the attack.
