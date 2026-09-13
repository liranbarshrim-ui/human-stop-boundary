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
| A-06 | alternate interface | **PASS within the tested Linux deployment boundary**: the public `PrivilegedDispatcher.execute` endpoint is absent; an unprivileged process successfully imported the class and attempted the former API, which failed; the privileged dispatcher runs as a separate OS identity; protected root, Store, secret, and IPC socket are permission-bound; unauthorized direct filesystem/socket access was rejected, while authorized IPC succeeded. This is deployment-bounded evidence, not a production security certification. |
| A-07 | confused deputy | PASS for principal binding in `EffectGate` |
| A-08 | parameter substitution | **PASS for the registered Gate/IPC boundary**: capability MAC binds deterministic canonical `params_digest`; post-issuance substitution is rejected; NFC-equivalent strings canonicalize identically; Unicode-colliding keys and duplicate JSON object keys are rejected; non-integral/non-finite floats are rejected. |
| A-09 | recovery replay | PASS for the basic consumed-capability replay path; recoverable adapter semantics remain adapter-dependent |
| A-10 | journal/store tampering | PASS for Store MAC integrity in the tested path |
| A-11 | adapter false-success | PASS for the recoverable path: `COMMITTED` status is required before finalization |
| A-12 | boundary ambiguity/path escape | PASS for absolute and parent-traversal paths in the tested dispatcher |

## Critical findings

A-06 is now closed **within the registered Linux deployment boundary**. The exact regression was exercised live: an unprivileged `nobody` process imported `PrivilegedDispatcher` and attempted the former `execute` API; the attempt was denied and produced no protected effect. The same live run also verified protected filesystem/secret/Store/socket access, authorized IPC, and parameter substitution rejection. This does not cover kernel compromise, privileged-process compromise, deployment misconfiguration, or every conceivable alternate interface.

A-08 transport/canonicalization gaps are now closed **within the registered protocol**. The transport rejects duplicate JSON object keys, canonicalization applies NFC normalization to strings and object keys, Unicode-colliding keys are rejected, numeric ambiguity is rejected, and Kernel uses the shared canonicalization implementation rather than a duplicate implementation.

The A-08 differential artifact is deliberately classified as **self-authored differential reproduction**, not independent implementation. It does not import DAR internals and is useful for detecting implementation/encoding drift, but it is not replication by an unrelated team. Genuine external replication remains an epistemic validation target rather than an unresolved implementation hole.

## Canonicalization requirements

1. deterministic object-key ordering;
2. NFC normalization of Unicode strings and object keys;
3. rejection of distinct keys that collide after NFC normalization;
4. rejection of duplicate JSON object keys at transport parsing;
5. rejection of non-integral and non-finite floats;
6. deterministic UTF-8 JSON encoding;
7. one shared canonicalization implementation used by Kernel and transport parsing.

## Evidence

- A-06 live workflow run `34768285345` completed successfully on commit `27aa63a479a346a044d45183dd2285007a901535`.
- The live job explicitly reported PASS for the unprivileged direct-import/old-API regression, protected resources, authorized IPC, and parameter substitution.
- Conformance run `34768285362` completed successfully on the same commit.

## Classification rule

`PASS` means the specific declared property was observed under the stated test conditions. It does not mean production security certification or universal coverage. Any future boundary or canonicalization change requires new pre-registered evidence.

The correct research claim is therefore bounded: A-06 and A-08 have passed their registered empirical tests; the prototype remains subject to deployment assumptions, privileged-process/kernel threat limits, adapter-dependent semantics, and genuinely independent external replication.
