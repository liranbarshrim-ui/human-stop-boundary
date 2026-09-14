# DAR Protected-Effect Semantics v1

Status: SPECIFICATION / REQUIRED FOR V2 CORE VALIDATION

## 1. Protected commit

`protected_commit(e)` denotes the externally observable commit of protected effect instance `e`, not merely a DAR journal record.

A DAR journal record with status `COMMITTED` is evidence about the enforcement mechanism. It is not, by itself, the definition of the real-world effect.

## 2. Boundary requirement

For a v2 claim, the protected effect MUST be specified at the level of the outcome DAR intends to prevent.

Examples may include:

- a durable database mutation;
- an externally delivered message that causes the protected state transition;
- a filesystem mutation when that mutation itself is the protected outcome;
- an external API action when that action is the protected outcome.

A syscall, `open`, `write`, adapter invocation, or journal entry is not automatically the protected outcome.

## 3. Crash semantics

The following trace is explicitly distinguished:

`adapter.execute -> external side effect -> process crash -> refusal -> DAR REFUSED`

If the external side effect is already irreversible, the trace contains `protected_commit` even if DAR subsequently records `REFUSED`.

Therefore DAR MUST NOT claim that a later `REFUSED` record proves that the external effect did not occur.

## 4. Formal property

The intended v2 property is:

`valid_refusal(r,e) ∧ r ≺ protected_commit(e) ∧ A1 ∧ A9 => ¬reachable(protected_commit(e))`

where `r ≺ protected_commit(e)` means the valid refusal is durably ordered before the externally observable protected commit.

If the protected effect cannot be atomically coordinated with the enforcement boundary, the deployment MUST document that limitation and MUST NOT silently equate DAR state with world state.

## 5. Non-claims

DAR does not currently establish:

- prevention of an external side effect that occurs before a crash;
- transactional atomicity between Store, journal, and an arbitrary external system;
- compensation or rollback of an already irreversible external outcome;
- complete mediation of outcomes outside the independently audited boundary.
