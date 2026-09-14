# DAR Assumption Registry v2

Status: **PRE-REGISTERED / NOT INDEPENDENTLY VALIDATED**

Version 2 makes the two load-bearing environmental conditions explicit. DAR code does not establish either condition by itself.

| ID | Assumption | Verification target | Required for PASS |
|---|---|---|---|
| A1 | Protected effects are reachable only through the registered enforcement interfaces. | independent interface/escape audit covering all processes, IPC, filesystem, adapters, helpers, and alternate execution paths | Yes |
| A2 | The enforcement substrate cannot be modified by the adversary during the tested trace. | privilege/isolation audit | Yes |
| A3 | A valid authority credential cannot be forged under the stated credential model. | credential threat-model review | Yes |
| A4 | The refusal event is durably recorded before a protected commit can occur. | crash/race testing | Yes |
| A5 | The protected commit has an authoritative observable status. | adapter contract review | Yes |
| A6 | Recovery uses the same protected effect identity and parameter digest. | recovery adversarial tests | Yes |
| A7 | The declared boundary remains unchanged throughout a conformance run. | manifest hash and run evidence | Yes |
| A8 | Test results are evaluated against the frozen classification rules. | independent reproduction | Yes |
| A9 | A trusted monotonic anchor exists outside the Store rollback domain and rejects any Store sequence below its recorded floor. | deployment/anchor audit plus rollback restoration test | Yes |

## Independence rule

A future reviewer may reject, weaken, split, or replace any assumption. Such a change creates a new registry version and does not rewrite historical results.

## Critical conditions

**A1 is an environmental completeness condition, not an implementation fact.** A successful DAR gate test does not prove that every path capable of producing a protected effect is registered. A PASS for the v2 property requires an independent interface/escape audit.

**A9 is mandatory for anti-rollback.** HMAC authenticates a snapshot but does not establish freshness. Without an external monotonic anchor, restoration of an older valid snapshot remains possible and the anti-rollback property is not established.

## Scope discipline

An effect outside the pre-registered boundary is not evidence for or against the local property unless the manifest explicitly declares the path in-scope. DAR must not silently expand the boundary after observing an attack. Conversely, a deployment must not describe a local boundary result as system-wide control.
