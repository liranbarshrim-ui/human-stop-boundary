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
| A-06 | alternate interface | **PASS only for the tested Linux deployment after the exact direct-import regression test passes**: the public `PrivilegedDispatcher.execute` endpoint is absent; the privileged dispatcher runs as a separate OS identity; protected root, Store, secret, and IPC socket are permission-bound; unauthorized direct filesystem/socket access and direct unprivileged invocation of the former API are rejected, while authorized IPC succeeds. This remains deployment-bounded evidence, not a production security certification. |
| A-07 | confused deputy | PASS for principal binding in `EffectGate` |
| A-08 | parameter substitution | PASS for the registered Gate/IPC path only after transport and canonicalization tests pass: capability MAC binds a deterministic canonical `params_digest`; canonicalization uses NFC Unicode normalization, rejects Unicode-colliding keys, duplicate JSON object keys, and ambiguous/non-finite numeric representations. |
| A-09 | recovery replay | PASS for the basic consumed-capability replay path; recoverable adapter semantics remain adapter-dependent |
| A-10 | journal/store tampering | PASS for Store MAC integrity in the tested path |
| A-11 | adapter false-success | PASS for the recoverable path: `COMMITTED` status is required before finalization |
| A-12 | boundary ambiguity/path escape | PASS for absolute and parent-traversal paths in the tested dispatcher |

## Critical findings

A-06 is not considered closed merely because the public Python endpoint was removed. Closure requires live Linux process/OS evidence plus the exact regression test in which an unprivileged process imports `PrivilegedDispatcher` and attempts the former `execute` API. The deployment claim remains bounded to the tested process/identity and filesystem/socket configuration.

A-08 evidence is deliberately classified as **self-authored differential reproduction**, not independent implementation. It is useful for detecting implementation/encoding drift because it does not import DAR internals, but it is not evidence of replication by an unrelated team. A genuinely independent reproduction remains an external research target.

Canonicalization requirements now include:
1. deterministic object-key ordering;
2. NFC normalization of Unicode strings and object keys;
3. rejection of distinct keys that collide after NFC normalization;
4. rejection of duplicate JSON object keys at transport parsing;
5. rejection of non-integral and non-finite floats;
6. deterministic UTF-8 JSON encoding.

## A-06 live evidence

The live workflow must rerun after the direct-import regression test is added. A successful run must explicitly report the unprivileged direct-import/old-API attempt as PASS before A-06 may be classified PASS.

## Classification rule

`PASS` means the specific declared property was observed under the stated test conditions. `HARDENED / PENDING LIVE OS VALIDATION` is not a PASS and is not converted into PASS by post-hoc narrowing of the claim. Any future boundary change requires a new pre-registered manifest and new evidence.

The correct research claim is therefore bounded: the prototype demonstrates several enforceable properties inside its registered boundary; A-06 requires and is being tested against an explicit unprivileged direct-API regression in addition to OS/process isolation; A-08 parameter binding now has explicit transport and Unicode canonicalization controls; and genuinely independent external reproduction remains unresolved.
