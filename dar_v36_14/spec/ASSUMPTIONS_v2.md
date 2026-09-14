# DAR Assumption Registry v3 — Outcome-Fenced Safety

Status: **PRE-REGISTERED / NOT INDEPENDENTLY VALIDATED**

The v3 strong property adds the external atomicity condition required to turn an advisory fence check into an outcome-level safety claim.

| ID | Assumption | Verification target | Required for PASS |
|---|---|---|---|
| A1 | Protected effects are reachable only through registered enforcement interfaces. | independent interface/escape audit | Yes |
| A2 | The enforcement substrate cannot be modified by the adversary during the tested trace. | privilege/isolation audit | Yes |
| A3 | A valid authority credential cannot be forged under the stated credential model. | credential threat-model review | Yes |
| A4 | Refusal is durably represented before a stale protected commit can be accepted. | crash/race testing | Yes |
| A5 | Protected commit has authoritative observable status. | adapter contract review | Yes |
| A6 | Recovery uses the same outcome identity and parameter digest. | recovery adversarial tests | Yes |
| A7 | The declared boundary remains unchanged throughout a conformance run. | manifest hash and run evidence | Yes |
| A8 | Results are evaluated against frozen classification rules. | independent reproduction | Yes |
| A9 | A trusted monotonic anchor exists outside the Store rollback domain. | deployment/anchor audit plus rollback restoration test | Yes |
| A10 | Fence advancement and protected external commit are serialized by the same authoritative external mechanism. | independent adapter/transaction audit plus adversarial race test | Yes |
| A11 | No alternate interface can create the protected outcome without the same authoritative fence. | independent completeness/escape audit | Yes |
| A12 | Repeated accepted commits are idempotent for the protected outcome. | retry/crash/replay testing | Yes |

## Critical conditions

**A1 is environmental.** DAR tests do not prove completeness by themselves.

**A9 is mandatory for anti-rollback.** Snapshot authentication does not establish freshness.

**A10 is mandatory for the strong `NO => no later outcome` claim.** A DAR-side `current_fence()` check is only advisory. The decisive safety check must occur atomically at the external commit point. If a race can advance the fence between the advisory read and the external operation, the external operation must reject the stale epoch without producing the protected outcome.

**A11 closes alternate-path bypass.** A fence protecting one API does not protect a second API, direct database path, recovery worker, subprocess, or side channel unless those paths are covered by the same authoritative enforcement point.

**A12 prevents replay from creating additional protected outcomes after a successful commit.**

## Classification discipline

Missing or independently unverified required conditions means **AMBIGUOUS / NOT PASS**. A local test suite cannot promote an external assumption to a fact.

## Scope discipline

The strong property is conditional on the frozen deployment and external contract. DAR must not silently expand the boundary after an attack and must not describe a bounded result as universal AI control.
