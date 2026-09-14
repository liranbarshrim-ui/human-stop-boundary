# DAR Protected-Effect Semantics v2

Status: SPECIFICATION / STRONG OUTCOME-FENCE PROFILE

## 1. Protected commit

`protected_commit(e)` denotes the externally observable irreversible outcome DAR intends to prevent, not a DAR journal record.

A DAR journal record with status `COMMITTED` is mechanism evidence only. It is never the definition of the real-world outcome.

## 2. Two identities are mandatory

`effect_id` identifies a protocol invocation. It is NOT the semantic identity of the protected outcome.

`outcome_key` identifies the stable external outcome being fenced. It MUST be supplied by the deployment/business protocol and MUST NOT be inferred from `effect_id` or blindly derived from parameters.

A valid protected capability and a valid protected refusal MUST bind cryptographically to the same `outcome_key`.

## 3. Strong outcome-fence contract

The strong DAR profile requires an external `FencedEffectAdapter` (or an independently equivalent mechanism) with:

1. an authoritative monotonic fence per `outcome_key`;
2. atomic fence advancement for refusal;
3. an atomic protected commit operation that succeeds only when its fence is still current;
4. durable idempotency by the protected transaction key;
5. authoritative recovery status for the same external transaction;
6. no protected side effect outside the fenced commit operation.

Critical invariant:

`refusal_fence(outcome_key) > commit_fence(outcome_key) => protected_commit(outcome_key) is impossible`

The external system, not the DAR process, must enforce the final atomicity point.

## 4. Crash semantics

The old unsafe trace remains explicitly rejected as a proof strategy:

`adapter.execute -> external side effect -> process crash -> refusal -> DAR REFUSED`

A later `REFUSED` record cannot erase an already-existing world outcome.

Under the strong profile, the irreversible side effect is permitted only inside the externally fenced commit operation. A crash before the fenced commit leaves no committed protected outcome; a crash after it may leave an outcome recoverable as `COMMITTED`, but a later refusal cannot retroactively classify that earlier commit as absent.

Safety ordering is established at the external fence, not by journal ordering.

## 5. Strong property

For an in-boundary protected outcome `e`:

`VALID_PROTECTED_REFUSAL(r,e) ∧ refusal_fence(e) advanced ∧ FENCED_ADAPTER(e) => ¬protected_commit(e) after the refusal fence`

Equivalently, once the external refusal fence is durably advanced for the outcome, no later external protected commit for that outcome can succeed.

This is the DAR operational target:

> **NO ⇒ outcome לא קרה**

Precise temporal meaning: **NO must be established before the external commit point, and the external system must enforce the fence.**

## 6. Non-claims

DAR still does not claim to control arbitrary external systems. An adapter that can make irreversible effects without the fence is outside the strong profile. In that deployment the correct result is `NOT PASS`, not an inference that `DAR REFUSED` means the world outcome did not occur.
