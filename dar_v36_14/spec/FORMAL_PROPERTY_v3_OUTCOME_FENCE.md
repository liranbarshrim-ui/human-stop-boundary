# DAR Formal Safety Property v3 — Outcome-Fenced NO

## Scope

This specification strengthens the DAR property from **no protected journal commit** to the narrower externally observable claim:

> **After an authenticated protected refusal has advanced the authoritative external fence for outcome `O`, no later protected operation may produce outcome `O`.**

This is a conditional safety property. It is not a theorem about arbitrary external systems.

## Definitions

- `O` — canonical `outcome_key`, identifying the real-world protected outcome, not merely an invocation/effect identifier.
- `F(O)` — authoritative monotonic fence maintained by the same external authority that can produce `O`.
- `R(O,e)` — authenticated refusal that advances the fence for `O` to epoch `e`.
- `C(O,e)` — protected external commit request carrying `O` and epoch `e`.

## Required external contract

The adapter is admissible for the strong property only if all of the following hold:

1. **Atomic fence check:** `C(O,e)` checks the current authoritative `F(O)` and produces no protected external outcome unless `F(O)=e`.
2. **Atomic serialization:** fence advancement and protected commit are serialized by the same authoritative external mechanism. A local `current_fence()` read is advisory only and is never the safety boundary.
3. **Monotonic fence:** `F(O)` never decreases.
4. **No side channel:** no protected path can produce `O` without passing through the same authoritative fence.
5. **Idempotency:** retries of the same accepted commit cannot create an additional protected outcome.
6. **Authoritative status:** recovery status refers to the same external transaction/outcome, not merely a local journal record.

## Safety invariant

For every admissible execution trace `T`:

`refusal_advanced(O,e,T) ∧ later_protected_attempt(O,e',T) ∧ e' < F(O,T) => ¬external_outcome(O,T)`

More directly, after the refusal fence is durably advanced:

`F(O) > e  =>  protected_commit(O,e) is impossible`

The pre-check in DAR is **not** part of this proof. The decisive check is the atomic check performed by the external authority at the commit point.

## Crash rule

A crash between external outcome creation and local journal publication MUST NOT be interpreted as non-occurrence. Recovery must query the authoritative external status. If status is `COMMITTED`, the outcome occurred; if status is genuinely `UNKNOWN`, the result is `UNKNOWN`, not `NO`.

A crash after external fence advancement but before local refusal publication may reduce availability, but must not permit a stale protected outcome.

## Outcome identity rule

`effect_id` identifies a protocol invocation. It is insufficient as the sole identity of a real-world outcome. Protected refusals and protected commits MUST bind to the same explicit `outcome_key`.

`params_digest` is an integrity check on parameters, not a substitute for business/outcome identity.

## PASS criterion

A deployment may classify this property **PASS** only when:

- A1 interface completeness is independently established;
- the external monotonic fence is independently verified;
- the external atomic fence/commit contract is independently verified;
- crash, retry, race, rollback, and alternate-path attacks are executed against the frozen deployment;
- every required attack has PASS evidence; and
- no in-boundary counterexample exists.

Missing external evidence is **AMBIGUOUS / NOT PASS**.

## Non-claim

DAR does not prove that an arbitrary database, API, operating system, actuator, financial system, or AI obeys this contract. The external system must provide and independently substantiate the enforcement point.
