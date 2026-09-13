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
| A-06 | alternate interface | **PASS within the tested Linux deployment boundary**: the public `PrivilegedDispatcher.execute` endpoint has been removed; the privileged dispatcher runs as a separate OS identity; protected root, Store, secret, and IPC socket are permission-bound; unauthorized direct filesystem/socket access and parameter substitution were rejected, while authorized IPC succeeded. This is deployment-bounded evidence, not a production security certification. |
| A-07 | confused deputy | PASS for principal binding in `EffectGate` |
| A-08 | parameter substitution | PASS for the registered Gate/IPC path: capability MAC binds a deterministic canonical `params_digest`; supplied parameters must match it. Canonicalization rejects ambiguous/non-integral/non-finite numeric representations |
| A-09 | recovery replay | PASS for the basic consumed-capability replay path; recoverable adapter semantics remain adapter-dependent |
| A-10 | journal/store tampering | PASS for Store MAC integrity in the tested path |
| A-11 | adapter false-success | PASS for the recoverable path: `COMMITTED` status is required before finalization |
| A-12 | boundary ambiguity/path escape | PASS for absolute and parent-traversal paths in the tested dispatcher |

## Critical findings

A-06 has now passed the registered live OS/process validation for the tested Linux configuration. The evidence includes separate OS identities, filesystem permissions, socket permissions, unauthorized direct-access attempts, authorized IPC, and post-issuance parameter substitution. The claim remains bounded to the tested deployment configuration and does not constitute a production security certification.

1. **A-06 — alternate interface:** live validation demonstrated that the tested unprivileged identity could not reach the privileged process through the tested alternate routes: protected filesystem, Store, secret, socket replacement, or unauthorized socket connection. The supported Python interface also has no public `PrivilegedDispatcher.execute` endpoint. The remaining security assumption is that deployment preserves the tested process/OS boundary and does not grant equivalent privileged access by an untested route.
2. **A-08 — parameter binding:** authorization is bound to the canonical parameter representation before the capability MAC is issued. The Gate recomputes that digest at execution/recovery time, so a substitution after issuance is rejected inside the registered boundary.

## A-06 live evidence

GitHub Actions workflow `DAR Live OS Boundary` completed successfully on commit `3c74ddc9b064695bea56db0101462f7de3690568` (run `34767671747`). The live job executed the two-UID boundary test successfully. The workflow stages the privileged runtime outside the repository workspace and runs the boundary test with real Linux account separation and filesystem/socket permissions.

The live result is stronger than a unit-test-only result, but it remains a test-environment observation. It does not establish resistance to kernel compromise, privileged-process compromise, deployment misconfiguration, or all possible alternate interfaces.

## Classification rule

`PASS` means the specific declared property was observed under the stated test conditions. `HARDENED / PENDING LIVE OS VALIDATION` is not a PASS and is not converted into PASS by post-hoc narrowing of the claim. Any future boundary change requires a new pre-registered manifest and new evidence.

The correct research claim is therefore bounded: the prototype demonstrates several enforceable properties inside its registered boundary; A-06's public alternate endpoint has been removed and the tested Linux process/OS boundary has passed live validation; A-08 parameter binding is cryptographically hardened; and deployment-level assumptions remain subject to independent reproduction and broader validation.
