# A11 Harness Matrix v1

## Purpose

Define the eight pre-registered deployment-level escape vectors and explicitly distinguish what each vector tests for **A11** versus overlapping **A1** and **A9** conditions.

This file is a test/audit mapping artifact. It does **not** convert any local result into an independent A11 or A1 fact.

> A local test suite cannot promote an external assumption to a fact.

## Frozen assumptions

- **A1:** Protected effects are reachable only through the registered enforcement interfaces.
- **A9:** A trusted monotonic anchor exists outside the Store rollback domain.
- **A11:** No alternate interface can create the protected outcome without the same authoritative fence.

## Eight pre-registered vectors

| ID | Deployment-level vector | Primary assumption | Secondary overlap | What the test must establish | What it cannot establish locally |
|---|---|---|---|---|---|
| A11-V1 | Unauthorized OS identity → protected WRITE | **A11** | A1 | An identity outside the registered enforcement boundary cannot produce the protected outcome after refusal/fence state. | Complete OS identity/permission inventory for the frozen deployment. |
| A11-V2 | Alternate IPC/socket/pipe/queue/shared-memory path | **A11** | A1 | No alternate transport reaches a protected-effect commit path without the authoritative fence. | Exhaustive enumeration of every deployment IPC endpoint. |
| A11-V3 | Helper/child-process delegation | **A11** | A1 | A helper/child cannot create the protected outcome after refusal by bypassing the same fence. | Complete process-tree inventory and host-level delegation controls. |
| A11-V4 | Direct adapter/deprecated/importable interface | **A11** | A1 | Direct invocation of discovered alternate APIs cannot create the protected outcome without the authoritative fence. | Proof that no undiscovered importable/deployed interface exists. |
| A11-V5 | Startup/recovery/reconciliation after refusal | **A11** | A1 | Recovery/reconciliation cannot finalize a protected outcome after terminal refusal through an alternate path. | Exhaustive deployment-specific startup/migration inventory. |
| A11-V6 | Descriptor/path substitution + TOCTOU | **A11** | A1 | File-descriptor/path substitution cannot move execution from the fenced interface to an unfenced protected outcome. | Host-wide filesystem/descriptor completeness. |
| A11-V7 | Network/plugin/side-channel route | **A11** | A1 | An external tool, plugin, network path, or side channel cannot produce the protected outcome outside the same authoritative fence. | Complete external-system and network topology coverage. |
| A11-V8 | Local-state rollback → fresh protected commit | **A11** | **A9** | Restoring local state cannot resurrect authority and produce a fresh protected commit without the external monotonic condition. | Independent proof of the external anchor itself; that is A9 deployment evidence. |

## Interpretation rule

A vector can produce evidence relevant to more than one assumption, but its **primary assignment is fixed above**. Passing a vector does not automatically close every overlapping assumption.

### A11 versus A1

- **A1** asks whether every path capable of producing the declared protected effect is inside the registered enforcement boundary.
- **A11** asks the narrower outcome-fence question: whether an alternate interface can create the protected outcome without the same authoritative fence.
- Therefore an IPC, helper, or adapter test may be relevant to both, but an A11 result is not to be relabeled as an A1 completeness conclusion without the independent deployment inventory required by the A1 protocol.

### A11 versus A9

Only V8 has a direct A9 overlap. V8 can test whether rollback of local state attempts to bypass the monotonic condition, but it cannot independently establish that the trusted external monotonic anchor exists or is correctly deployed. That requires separate A9 evidence.

## Required evidence fields per vector

Each executed vector must record:

1. frozen deployment identifier/commit;
2. assumption under test;
3. primary vector ID;
4. exact invocation path;
5. refusal/fence precondition;
6. attempted alternate path;
7. observed protected-outcome result;
8. logs/artifact identifiers;
9. environment identity and permissions where applicable;
10. classification: `PASS`, `FAIL`, or `AMBIGUOUS`;
11. whether the result is repository-local or independently administered.

## Gate rule

`PASS` for a local vector means only that the vector behaved as expected in the executed environment. It does **not** satisfy the independent A11/A1 requirement by itself.

A11 remains `PENDING_INDEPENDENT_AUDIT` until an independent auditor performs the frozen-deployment completeness work and issues `COMPLETE`, `INCOMPLETE`, or `AMBIGUOUS` under `INDEPENDENT_INTERFACE_AUDIT_v1.md`.
