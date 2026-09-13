# Invitation to Researchers

## Try to break DAR

DAR (Decision Accountability Review) is an active research prototype. It is not presented as production-certified security, and it is not asking for endorsement.

**Researchers, security engineers, formal-methods researchers, AI-safety researchers, and skeptical reviewers are invited to try to falsify it.**

The central question is simple:

> If a named human authority says **NO**, can the process continue anyway?

Do not assume the answer is no. Try to make it yes.

## What to attack

The repository contains an executable attack catalog covering A-01 through A-12, including:

- capability/effect execution-path failures
- concurrent duplicate execution
- replay
- stale capabilities
- rollback assumptions
- alternate interfaces / boundary bypass
- confused deputy behavior
- parameter substitution
- recovery replay
- Store/journal tampering
- adapter false-success
- boundary ambiguity and path escape

The repository also contains live Linux process/identity tests for the A-06 boundary and canonicalization/transport tests for A-08.

## How to participate

1. Clone the public repository.
2. Read `ATTACK_CATALOG_v1.md`, `SECURITY.md`, `AUDIT_v36_14.md`, and `spec/EMPIRICAL_STATUS_v1.md`.
3. Run the normal test/conformance suite.
4. Run the live Linux boundary workflow where applicable.
5. Attempt attacks that are **not** already covered.
6. If you find a failure, document the smallest reproducible case and the exact boundary/assumption it violates.

A successful attack is valuable research result. Please report it rather than trying to make the system look better by narrowing the claim after the fact.

## What counts as a useful finding

Particularly valuable findings include:

- a path by which an unauthorized principal can cause a protected effect;
- a way to reuse, substitute, forge, or transform an authorization into a different effect;
- a process, filesystem, IPC, recovery, rollback, or serialization bypass;
- a discrepancy between the documented security boundary and the executable implementation;
- an attack that works despite all currently registered controls;
- a hidden assumption required for a claimed property to hold.

Please distinguish clearly between:

- **implementation failure** — the code violates a registered property;
- **deployment failure** — the property depends on an environmental condition that is absent;
- **model failure** — the property does not actually establish the security claim being made;
- **scope failure** — the attack is outside the declared boundary, but exposes an important limitation.

## No endorsement required

The project explicitly welcomes negative results, failed hypotheses, and criticism. A researcher does not need to agree with DAR's premises to participate.

The strongest result is not "DAR works." The strongest result is a reproducible answer to the question:

> **Can the claimed boundary actually be enforced under the stated conditions?**

## Current evidence and limitations

Current empirical status is recorded in `spec/EMPIRICAL_STATUS_v1.md`. A green CI run is evidence for the tested configuration; it is not an independent security certification.

A-06 currently has live Linux evidence for the tested process/identity/filesystem/socket configuration. A-08 has self-authored differential reproduction; genuinely independent external replication remains an open research target.

Please read the declared assumptions before interpreting any PASS result.

## Responsible disclosure

If a finding could expose a real system, credential, private data, or third-party service, do not exploit it beyond what is necessary to establish reproducibility. Prefer a minimal proof of concept, remove secrets from reports, and report privately before public disclosure when appropriate.

Public repository:

https://github.com/liranbarshrim-ui/human-stop-boundary

Research site:

https://matrix-audit.com

**Author:** Liran Bar-Shrim
