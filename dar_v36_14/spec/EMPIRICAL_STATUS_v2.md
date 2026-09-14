# DAR Boundary Conformance — Empirical Attack Status v2

Status: **PRE-REGISTERED / PENDING REQUIRED EVIDENCE**

Version 2 does not promote the existing prototype tests to a stronger claim. It makes the two previously load-bearing environmental conditions explicit before a PASS can be claimed for the core property.

| Condition | Required evidence | Current status |
|---|---|---|
| External monotonic anchor (A9) | deployment-specific anchor plus rollback restoration test | **PENDING** |
| Interface completeness (A1) | independent interface/escape audit covering all protected-effect paths | **PENDING** |
| Registered-path attack probes A-01–A-12 | executable test suite | Existing bounded evidence only |

## Interpretation

The existing A-05 test demonstrates rejection of a Store state below a supplied anchor. It does **not** prove that every deployment has such an anchor. A deployment without an external anchor must not receive PASS for anti-rollback.

The existing A-06/path tests provide deployment-bounded evidence for the tested Linux configuration. They do **not** constitute an independent completeness audit. A deployment must obtain that audit before claiming the v2 core property.

## Required next validation

1. Freeze a concrete deployment and anchor implementation.
2. Independently enumerate every path capable of producing the protected WRITE effect.
3. Run the rollback restoration attack against the frozen deployment.
4. Run the interface/escape audit and preserve its evidence separately from DAR-authored tests.
5. Only then classify the v2 core property as PASS, FAIL, or AMBIGUOUS under the frozen rules.

Until these steps are complete, the repository's defensible claim is **conditional local enforcement**, not demonstrated system-wide human control.
