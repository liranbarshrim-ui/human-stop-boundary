# DAR Boundary Conformance — Empirical Attack Status v1

Status: PRE-REGISTERED / RESEARCH

The test suite `tests/test_attack_empirical.py` contains executable probes for A-01 through A-12 in `ATTACK_CATALOG_v1.md`.

This file records what the probes mean. A green unit-test run is **not** equivalent to a secure result for every attack family.

| ID | Probe | Current interpretation |
|---|---|---|
| A-01 | capability/effect execution path | PASS for the registered gate path; no standalone refusal primitive exists in this prototype |
| A-02 | concurrent duplicate execution | PASS: durable consumption rejects the second use |
| A-03 | replay | PASS: consumed nonce/txid/effect key reject replay |
| A-04 | stale capability | PASS: capability epoch must match current state |
| A-05 | rollback | PASS **conditional on** a trusted external monotonic anchor; without one this is an assumption |
| A-06 | alternate interface | **BOUNDARY LIMITATION**: `PrivilegedDispatcher` can be called directly. The registered conformance boundary is `EffectGate`/`DispatcherClient`; arbitrary callers are outside that declared boundary unless explicitly routed through it |
| A-07 | confused deputy | PASS for principal binding in `EffectGate` |
| A-08 | parameter substitution | **BOUNDARY LIMITATION**: the current `EffectRequest` does not bind a parameter digest for `execute()`. The dispatcher receives parameters separately. This must not be reported as a PASS |
| A-09 | recovery replay | PASS for the basic consumed-capability replay path; recoverable adapter semantics remain adapter-dependent |
| A-10 | journal/store tampering | PASS for Store MAC integrity in the tested path |
| A-11 | adapter false-success | PASS for the recoverable path: `COMMITTED` status is required before finalization |
| A-12 | boundary ambiguity/path escape | PASS for absolute and parent-traversal paths in the tested dispatcher |

## Critical findings

A-06 and A-08 are deliberately retained as visible limitations rather than hidden behind a green test suite.

1. **A-06 — alternate interface:** the enforcement boundary is only meaningful if all protected effects are forced through the registered interface. This is assumption A1 and remains the highest-risk assumption.
2. **A-08 — parameter binding:** capability authorization currently binds action/effect identity, but the basic `execute()` path does not cryptographically bind the requested parameters. A future conformance revision should bind a canonical parameter digest to the authorization record before treating parameter-substitution resistance as PASS.

## Classification rule

`PASS` means the specific declared property was observed under the stated test conditions. `BOUNDARY LIMITATION` is not a PASS and is not converted into PASS by post-hoc narrowing of the claim. Any future boundary change requires a new pre-registered manifest and new evidence.

The correct research claim is therefore bounded: the prototype demonstrates several enforceable properties inside its registered boundary while exposing concrete remaining attack surfaces at alternate interfaces and parameter binding.
