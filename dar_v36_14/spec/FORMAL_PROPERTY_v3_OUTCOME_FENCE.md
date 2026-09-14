# DAR Formal Safety Property v3 — Outcome-Fenced NO

## Scope

This specification strengthens the DAR property from **no protected journal commit** to the narrower externally observable claim:

> **After an authenticated protected refusal has installed an authoritative terminal refusal for outcome `O`, no later protected operation may produce outcome `O`.**

This is a conditional safety property. It is not a theorem about arbitrary external systems.

## Definitions

- `O` — canonical `outcome_key`, identifying the real-world protected outcome, not merely an invocation/effect identifier.
- `F(O)` — authoritative monotonic commit fence maintained by the same external authority that can produce `O`.
- `R(O,e,r)` — authenticated refusal that atomically installs terminal refusal identity `r` for `O` at fence epoch `e`.
- `Q(O)` — authoritative terminal refusal state for `O`; once true, it cannot be cleared by a numeric fence update.
- `C(O,e)` — protected external commit request carrying `O` and epoch `e`.

## Required external contract

The adapter is admissible for the strong property only if all of the following hold:

1. **Atomic refusal publication:** refusal installation advances/records the external fence and terminal refusal state as one authoritative operation.
2. **Atomic commit exclusion:** `C(O,e)` is serialized by the same authority and rejects if `Q(O)` is true; otherwise it produces no protected outcome unless `F(O)=e`.
3. **Atomic serialization:** refusal installation and protected commit are mutually serialized by the same authoritative external mechanism. A local `current_fence()` read is advisory only and is never the safety boundary.
4. **Monotonic fence:** `F(O)` never decreases.
5. **Terminal refusal:** once `Q(O)` is true, no operation can clear it, replace it with an unrelated refusal, or make `O` commit by presenting the same numeric epoch.
6. **No side channel:** no protected path can produce `O` without passing through the same authoritative refusal/fence enforcement point.
7. **Idempotency:** retries of the same accepted commit cannot create an additional protected outcome; retries of the same refusal identity are idempotent.
8. **Authoritative status:** recovery status refers to the same external transaction/outcome, not merely a local journal record.

## Safety invariant

For every admissible execution trace `T`:

`Q(O,T) ∧ later_protected_attempt(O,e',T) => ¬external_outcome(O,T)`

Before terminal refusal, a commit may legitimately win the race. Therefore DAR does **not** claim retroactive cancellation of an already-created outcome.

The numeric fence remains a freshness/serialization constraint:

`¬Q(O,T) ∧ later_protected_attempt(O,e',T) ∧ e' != F(O,T) => ¬external_outcome(O,T)`

The terminal refusal state is what closes the crash/equality gap: `Q(O)` remains true even when local DAR state has rolled back to an epoch numerically equal to the refusal epoch.

The pre-check in DAR is **not** part of this proof. The decisive checks are performed atomically by the external authority at the refusal and commit points.

## Crash rule

A crash between external outcome creation and local journal publication MUST NOT be interpreted as non-occurrence. Recovery must query the authoritative external status. If status is `COMMITTED`, the outcome occurred; if status is genuinely `UNKNOWN`, the result is `UNKNOWN`, not `NO`.

A crash after external terminal refusal publication but before local refusal publication may reduce availability, but must not clear `Q(O)` or permit a later protected outcome.

## Outcome identity rule

`effect_id` identifies a protocol invocation. It is insufficient as the sole identity of a real-world outcome. Protected refusals and protected commits MUST bind to the same explicit `outcome_key`.

`params_digest` is an integrity check on parameters, not a substitute for business/outcome identity.

## PASS criterion

A deployment may classify this property **PASS** only when:

- A1 interface completeness is independently established;
- the external monotonic fence is independently verified;
- terminal refusal durability and irreversibility are independently verified;
- the external atomic refusal/commit exclusion contract is independently verified;
- crash, retry, race, rollback, and alternate-path attacks are executed against the frozen deployment;
- every required attack has PASS evidence; and
- no in-boundary counterexample exists.

Missing external evidence is **AMBIGUOUS / NOT PASS**.

## Non-claim

DAR does not prove that an arbitrary database, API, operating system, actuator, financial system, or AI obeys this contract. The external system must provide and independently substantiate the enforcement point.
