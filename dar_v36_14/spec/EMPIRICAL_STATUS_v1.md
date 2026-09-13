# DAR Boundary Conformance — Empirical Attack Status v1

Status: PRE-REGISTERED / RESEARCH

The test suite `tests/test_attack_empirical.py` contains executable probes for A-01 through A-12 in `ATTACK_CATALOG_v1.md`.

A green unit-test run is **not** equivalent to a production security certification. Each classification is bounded by the declared boundary and assumptions.

| ID | Probe | Current interpretation |
|---|---|---|
| A-01 | capability/effect execution path | PASS for the registered gate path; no standalone refusal primitive exists in this prototype |
| A-02 | concurrent duplicate execution | PASS: durable consumption rejects the second use |
| A-03 | replay | PASS: consumed nonce/txid/effect key reject replay |
| A-04 | stale capability | PASS: capability epoch must match current state |
| A-05 | rollback | PASS **conditional on** a trusted external monotonic anchor; without one this is an assumption |
| A-06 | alternate interface | **HARDENED / PENDING LIVE OS VALIDATION**: the public `PrivilegedDispatcher.execute` endpoint has been removed; the registered IPC/Gate path calls only the internal `_apply` primitive. Process isolation, filesystem permissions, socket replacement, and cross-UID behavior still require live deployment validation |
| A-07 | confused deputy | PASS for principal binding in `EffectGate` |
| A-08 | parameter substitution | PASS for the registered Gate/IPC path: capability MAC binds a deterministic canonical `params_digest`; supplied parameters must match it. Canonicalization rejects ambiguous/non-integral/non-finite numeric representations |
| A-09 | recovery replay | PASS for the basic consumed-capability replay path; recoverable adapter semantics remain adapter-dependent |
| A-10 | journal/store tampering | PASS for Store MAC integrity in the tested path |
| A-11 | adapter false-success | PASS for the recoverable path: `COMMITTED` status is required before finalization |
| A-12 | boundary ambiguity/path escape | PASS for absolute and parent-traversal paths in the tested dispatcher |

## Critical findings

A-06 is no longer an exposed public alternate execution endpoint in the supported Python interface, but it is **not yet a final PASS** because the stronger criterion includes live OS/process isolation. A-08 has been hardened with an explicit canonical parameter profile and cryptographic parameter binding.

1. **A-06 — alternate interface:** the remaining question is deployment-level: whether an unprivileged identity can reach the privileged process, its Store, secret, protected filesystem, or socket by another route. This remains assumption A1 plus deployment controls until independently reproduced.
2. **A-08 — parameter binding:** authorization is bound to the canonical parameter representation before the capability MAC is issued. The Gate recomputes that digest at execution/recovery time, so a substitution after issuance is rejected inside the registered boundary.

## Classification rule

`PASS` means the specific declared property was observed under the stated test conditions. `HARDENED / PENDING LIVE OS VALIDATION` is not a PASS and is not converted into PASS by post-hoc narrowing of the claim. Any future boundary change requires a new pre-registered manifest and new evidence.

The correct research claim is therefore bounded: the prototype demonstrates several enforceable properties inside its registered boundary, A-06's public alternate endpoint has been removed, A-08 parameter binding is cryptographically hardened, and deployment-level boundary assumptions remain subject to live and independent validation.
