# DAR v36.14 — Hardened Security Candidate

Decision Accountability Review (DAR) is a research prototype for a bounded decision/effect boundary. Authorization is bound to a named principal, domain, effect class, state generation and process generation.

**DAR does not claim that it can universally stop an arbitrary AI system.** Its security claims apply only to effects actually routed through and controlled by the DAR enforcement boundary.

## v36.14 hardening

- Privileged-side capability verification and no caller-supplied Python callable across the boundary.
- Capability binding to principal, domain, action/effect class, mutation class, state digest and boot generation.
- Replay prevention and durable consumption.
- Attenuation-only permission transitions and governance mutation denial.
- Recoverable effect intent stored atomically with capability consumption.
- Recovery `params_digest` binding.
- Fail-closed journal preparation: no external effect executes if PREPARED cannot be recorded.
- Journal state-machine validation and immutable intent fields.
- COMMITTED requires authoritative adapter status.
- Optional monotonic anti-rollback anchor interface.
- `SO_PEERCRED` checks on every accepted connection.
- Dispatcher instance locking and bounded framed IPC.
- Filesystem, symlink and rename-race tests.
- Optional Linux `no_new_privs`, seccomp and Landlock hardening.

## Verification

Development environment result: **57 passed, 1 skipped** with `PYTHONPATH=. pytest -q`.

The skipped test is the optional Landlock test because the current kernel returns `ENOSYS`.

A live two-UID boundary test and a live `SIGKILL` generation test also pass in the supported development environment.

## Anti-rollback

HMAC authenticates a Store snapshot but cannot distinguish an older valid snapshot restored by an attacker. v36.14 therefore exposes a `MonotonicAnchor` interface. Production rollback protection requires a durable trust anchor outside the Store rollback domain. A second ordinary file on the same attacker-controlled filesystem is not sufficient.

Without an external anchor, DAR makes **no anti-rollback claim**.

## External exactly-once

DAR provides durable intent and recovery machinery. Exactly-once semantics for arbitrary external effects remain adapter-dependent. The adapter must provide an idempotency key and authoritative status; DAR records COMMITTED only after that status confirms COMMITTED.

## Status

Hardened research prototype, not production certification. See `SECURITY.md` and `AUDIT_v36_14.md`.
