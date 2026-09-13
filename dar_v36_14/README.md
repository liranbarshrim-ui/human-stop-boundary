# DAR v36.14 — Hardened Security Candidate

**Decision Accountability Review (DAR)** is a research prototype for enforcing a bounded decision/effect boundary: authorization is bound to a named principal, a domain, an effect class, a state generation and a process generation, and effects routed through the privileged boundary are subject to durable consumption and recovery rules.

> DAR does **not** claim that it can universally stop an arbitrary AI system. Its security claims apply only to effects actually routed through and controlled by the DAR enforcement boundary.

## Start here

- `DAR_DOCTRINE.md` — conceptual foundation and non-redundant principles.
- `SECURITY.md` — security boundary and explicit limitations.
- `AUDIT_v36_14.md` — verification record, findings addressed, and evidence provenance.

## What v36.14 hardens

- Privileged-side capability verification; the unprivileged client never receives the DAR secret and cannot submit Python callables.
- Capability binding to principal, domain, action/effect class, mutation class, state digest and boot generation.
- Replay prevention and durable capability/effect consumption.
- Attenuation-only permission transitions and governance mutation denial.
- Recoverable effect intent stored atomically with capability consumption.
- Recovery parameter binding through a durable `params_digest`.
- Fail-closed journal preparation: if PREPARED cannot be durably recorded, execution fails before the external effect is invoked.
- Journal state-machine validation, including immutable intent fields.
- COMMITTED is recorded only after authoritative adapter status reports COMMITTED.
- Monotonic Store-version advancement on effect mutations, so an external monotonic anchor detects rollback of effect-consumption state as well as authority state.
- Optional monotonic anti-rollback anchor interface for deployments with a trust anchor outside the Store rollback domain.
- Explicit pending-intent reconciliation for crashes or journal failures after external execution.
- Reconciliation verifies the supplied original parameters against `params_digest` and uses the adapter's idempotency/status contract rather than blindly replaying.
- Unix `SO_PEERCRED` identity checks on every accepted connection.
- Dispatcher instance locking.
- Bounded framed IPC with exact-read loops and maximum frame sizes.
- Filesystem boundary tests for traversal, absolute paths, symlink attacks and rename races.
- Optional Linux `no_new_privs`, seccomp and Landlock hardening.

## Verification in the development environment

- `PYTHONPATH=. pytest -q -v`: **60 passed, 1 skipped** (61 collected).
- The one skipped test is the optional Landlock test because the current kernel returns `ENOSYS`.
- `python -m pip install --no-deps --no-build-isolation .`: **PASS**.
- `python -m compileall -q dar tests`: **PASS**.
- Live two-UID boundary test: **PASS** for direct effect write denial, secret/state read denial, socket replacement denial, authorized IPC effect and malformed request rejection.
- Live `SIGKILL` generation test: **PASS**; a capability issued by the killed generation is rejected by the fresh dispatcher generation.

## Recovery semantics

The recoverable path is deliberately explicit:

1. The Store durably records the authorized, consumed intent.
2. A journal `PREPARED` record must be written before external execution.
3. The adapter executes under a stable idempotency key.
4. DAR requires authoritative adapter `COMMITTED` status before recording `COMMITTED`.
5. If a crash or journal/cleanup failure leaves an intent pending, `reconcile_pending()` can obtain the original parameters from an external `params_provider`, verify their digest, consult the adapter, retry only through the adapter's idempotent contract when status is UNKNOWN/PREPARED, and clear the Store intent only after COMMITTED is established.

If the deployment cannot supply the original parameters or the adapter cannot provide authoritative idempotency/status semantics, complete recovery is not established. An unresolved intent can remain pending and requires an external operational decision.

## Anti-rollback

The Store is authenticated with HMAC, but HMAC alone does not prevent an attacker from restoring an older **valid** snapshot. v36.14 therefore exposes an explicit `MonotonicAnchor` interface.

A deployment that needs rollback protection must connect this interface to a durable trust anchor outside the Store's rollback domain (for example, an appropriately protected hardware or remote monotonic service). A second ordinary file on the same attacker-controlled filesystem is not sufficient.

Without such an external anchor, DAR makes **no anti-rollback claim**. With an external anchor, the anchor covers authenticated Store versions, including effect-consumption and pending-intent mutations, provided every production mutation uses the Store write path.

## External exactly-once semantics

DAR provides durable intent and replay/recovery machinery. It cannot independently make an arbitrary external side effect exactly-once. The adapter must expose an idempotency key and an authoritative status operation. DAR records `COMMITTED` only after the adapter confirms that state.

## Linux hardening

The seccomp configuration is a deny-list rather than a complete syscall allow-list. Landlock is optional and requires a host kernel that supports it. These mechanisms are defense-in-depth and are not substitutes for deployment isolation or independent review.

## Security status

This is a **hardened research prototype, not a production certification**. Remaining work includes independent external red-team review, production-distribution testing, stronger identity/attestation, delegation semantics, deployment controls, complete effect-universe analysis and a production-grade external monotonic trust anchor where rollback protection is required.

See `SECURITY.md` and `AUDIT_v36_14.md` for the security boundary, limitations and verification record.
