# DAR Assumption Registry v3 — Outcome-Fenced Safety

Status: **PRE-REGISTERED / NOT INDEPENDENTLY VALIDATED**

The v3 strong property requires an external authority that couples the monotonic commit fence with a terminal outcome-refusal state. A numeric fence alone is insufficient after crashes that can leave local DAR state behind the external authority.

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
| A11 | No alternate interface can create the protected outcome without the same authoritative fence and refusal state. | independent completeness/escape audit | Yes |
| A12 | Repeated accepted commits are idempotent for the protected outcome. | retry/crash/replay testing | Yes |
| A13 | Terminal refusal state for `outcome_key` is durably authoritative and is atomically checked by the same external mechanism that can create the protected outcome; it cannot be cleared or bypassed by a numeric fence update. | refusal/commit crash, retry, rollback, and race audit | Yes |

## Critical conditions

**A1 is environmental.** DAR tests do not prove completeness by themselves.

**A9 is mandatory for anti-rollback.** Snapshot authentication does not establish freshness.

**A10 is mandatory for atomic exclusion.** A DAR-side `current_fence()` check is only advisory. The decisive safety check must occur atomically at the external commit point, sharing the same serialization authority as refusal publication.

**A11 closes alternate-path bypass.** A fence protecting one API does not protect a second API, direct database path, recovery worker, subprocess, or side channel unless those paths are covered by the same authoritative enforcement point and terminal refusal state.

**A12 prevents replay from creating additional protected outcomes after a successful commit.**

**A13 closes the crash/equality gap.** A fence value such as `2` does not distinguish “epoch 2 is current” from “epoch 2 became terminally refused.” The external authority therefore needs an explicit refusal marker (or independently equivalent terminal state) and `commit` must reject that outcome regardless of numeric fence equality. A crash after external refusal publication but before local DAR publication may reduce availability, but must not reopen the outcome.

## Classification discipline

Missing or independently unverified required conditions means **AMBIGUOUS / NOT PASS**. A local test suite cannot promote an external assumption to a fact.

## Scope discipline

The strong property is conditional on the frozen deployment and external contract. DAR must not silently expand the boundary after an attack and must not describe a bounded result as universal AI control.
