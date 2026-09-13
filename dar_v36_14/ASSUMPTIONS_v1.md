# DAR Assumptions Registry v1

**Status:** PUBLIC / PRE-REGISTERED  
**Layer:** Enforcement / evaluation  
**Date:** 2026-09-13

These assumptions are explicit conditions for the bounded non-bypass claim. They are **not** axioms of DAR and are not independently validated merely because the implementation declares them.

| ID | Assumption | Status |
|---|---|---|
| A1 | Every protected effect commit path is enumerated by the boundary manifest. | SELF_DECLARED |
| A2 | A protected effect cannot commit except through an enumerated commit path. | SELF_DECLARED |
| A3 | The designated authority credential cannot be forged within the threat model. | SELF_DECLARED |
| A4 | The enforcement substrate is trusted for the properties explicitly assigned to it. | SELF_DECLARED |
| A5 | The adversary cannot directly modify the enforcement substrate or its trusted root of authority. | SELF_DECLARED |
| A6 | The test harness can reliably observe the protected commit event. | SELF_DECLARED |
| A7 | The refusal event is uniquely identifiable and bound to the relevant transaction/effect. | SELF_DECLARED |
| A8 | Evaluation begins only after the boundary, assumptions, threat model and pass/fail criteria are frozen. | SELF_DECLARED |

## Independence rule

No DAR component may upgrade an assumption's status by assertion. `INDEPENDENTLY_REVIEWED` and `EMPIRICALLY_VALIDATED` require evidence external to the claim being evaluated.

## Falsification targets

Red-team evaluation should actively attempt to invalidate A1, A2, A3, A5 and A6. In particular, alternate interfaces, confused-deputy paths, replay, rollback, race conditions, capability substitution, and unobserved side effects should be treated as assumption attacks rather than silently excluded.

## Claim discipline

If an assumption fails, the correct conclusion is:

> The conditional claim was not established under the stated assumptions.

It is not valid to redefine the assumption after observing the attack and retain the same claim.
