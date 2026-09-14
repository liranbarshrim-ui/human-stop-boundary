# DAR Formal Safety Property v2

## Claim

Let `B` be the pre-registered enforcement boundary, `R` a valid refusal issued by the designated authority, and `C` a protected effect commit.

> **P(B): For every execution trace wholly inside B, if the required environmental conditions hold and R occurs, C is unreachable.**

Compact form:

`trace ⊆ B ∧ conditions(A1,A2,A3,A4,A5,A6,A7,A8,A9) ∧ valid_refusal(trace) => ¬reachable(protected_commit, trace)`

The two newly explicit load-bearing conditions are:

1. **A1 / interface completeness:** an independent audit establishes that every path capable of producing the declared protected effect is within the registered enforcement boundary.
2. **A9 / monotonicity:** a trusted monotonic anchor outside the Store rollback domain prevents restoration to a Store sequence below the recorded floor.

## Counterexample criterion

A trace satisfying all required conditions is a **FAIL** when:

`trace ⊆ B ∧ conditions(...) ∧ valid_refusal(trace) ∧ protected_commit(trace)`

A rollback trace without A9 is **not evidence that the v2 property fails**; it demonstrates that the required anti-rollback condition is absent and the deployment cannot claim PASS.

An escape trace that violates A1 is likewise not evidence of a v2 in-boundary failure until the independent audit establishes that the escaped path was actually part of B. It is evidence that the completeness condition is unresolved or false for that deployment.

## Classification discipline

- Missing or unverified required conditions: **AMBIGUOUS / NOT PASS**.
- Proven in-boundary counterexample with all conditions satisfied: **FAIL**.
- Effect outside a pre-registered boundary: **OUT-OF-SCOPE** only when the exclusion existed before the attack.
- Successful tests of the registered path alone do not establish system-wide control.

## Research status

This is a bounded, testable research property. It is not a theorem about arbitrary AI systems and does not constitute a production security certification or independent security audit.
