# DAR Assumption Registry v1

Status: **SELF-DECLARED / NOT INDEPENDENTLY VALIDATED**

These assumptions are part of the pre-registered research model. DAR does not establish their truth merely by executing its own code.

| ID | Assumption | Verification target |
|---|---|---|
| A1 | Protected effects are reachable only through the registered enforcement interfaces. | independent interface/escape audit |
| A2 | The enforcement substrate cannot be modified by the adversary during the tested trace. | privilege/isolation audit |
| A3 | A valid authority credential cannot be forged under the stated credential model. | credential threat-model review |
| A4 | The refusal event is durably recorded before a protected commit can occur. | crash/race testing |
| A5 | The protected commit has an authoritative observable status. | adapter contract review |
| A6 | Recovery uses the same protected effect identity and parameter digest. | recovery adversarial tests |
| A7 | The declared boundary remains unchanged throughout a conformance run. | manifest hash and run evidence |
| A8 | Test results are evaluated against the frozen classification rules. | independent reproduction |

## Independence rule

A future reviewer may reject, weaken, split, or replace any assumption. Such a change creates a new registry version and does not rewrite historical results.

## Critical warning

A1 is the highest-risk assumption. If an attacker can cause a protected WRITE effect through an unregistered interface, that is a boundary failure for any version whose manifest declares that effect protected.
