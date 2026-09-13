# Decision Accountability Review (DAR)

**A structural framework for making stop authority explicit, bounded, and testable.**

Defined by **Liran Bar-Shrim**.

> **Control is not the ability to move forward. Control is the ability to stop.**

When a decision becomes irreversible under uncertainty, DAR asks a simple question:

> **If the designated authority says “stop,” can the controlled process continue anyway?**

DAR treats that question as a structural property—not merely a matter of policy, trust, or good intentions.

## The doctrine

The core DAR principles are documented in [`dar_v36_14/DAR_DOCTRINE.md`](dar_v36_14/DAR_DOCTRINE.md):

- **Foundational Qualification** — a claimed authority must have defined standing and scope before it is relied upon.
- **Axiom 1 — Authority Self-Containment** — no authority may define, evaluate, modify, or override the conditions of its own authority.
- **Axiom 2 — No Sovereignty by Origin** — creation, ownership, operation, or origin does not by itself confer sovereign authority.
- **Freeze Principle** — a qualified boundary cannot be unilaterally relaxed by the actor operating within it.
- **Structural Irrevocability** — for the controlled effect universe, a valid stop must bind continuation through the boundary rather than merely request compliance.

The principles are deliberately non-redundant: each addresses a different route by which nominal authority can fail to become binding authority.

## The implementation

[`dar_v36_14/`](dar_v36_14/) contains the current **active research prototype**.

It implements a bounded enforcement boundary with:

- named principal/domain capability binding;
- explicit action/effect classes;
- state and process-generation binding;
- attenuation-only permission transitions;
- governance mutation denial;
- durable capability and effect consumption;
- recoverable effect intent and parameter-digest binding;
- fail-closed journal preparation;
- validated journal transitions;
- authoritative adapter `COMMITTED` confirmation;
- pending-intent reconciliation;
- Unix peer-credential checks;
- dispatcher instance locking;
- bounded framed IPC;
- filesystem and race-condition tests;
- optional Linux `no_new_privs`, seccomp and Landlock hardening;
- an explicit external monotonic-anchor interface for rollback detection.

## Verification

The verified development checkout was executed with:

**`PYTHONPATH=. pytest -q -v` → 60 passed, 1 skipped (61 collected).**

The single skip is the optional Landlock test because the host kernel returns `ENOSYS`.

Additional local checks passed: package installation, Python compilation, live two-UID boundary testing, and live `SIGKILL` generation-rotation testing.

The repository must be treated as the source of truth. Chat-pasted artifacts are not evidence until compared against a fresh checkout and executed.

## Security boundary and limits

DAR does **not** claim universal control over arbitrary AI systems. Its security claims apply only to effects actually routed through and controlled by the DAR enforcement boundary.

HMAC-authenticated state does not by itself prevent restoration of an older valid snapshot. Anti-rollback therefore requires a trusted monotonic anchor outside the Store rollback domain.

Exactly-once semantics for arbitrary external side effects remain dependent on an authoritative idempotent adapter.

Pending-intent reconciliation is bounded and deployment-dependent: `reconcile_pending()` requires an external `params_provider` to supply the original parameters, verifies their `params_digest`, consults authoritative adapter status, and retries UNKNOWN/PREPARED only through the adapter's idempotent contract. It clears the pending intent only after COMMITTED is established and the journal contains matching validated intent. If the deployment cannot supply the original parameters or the adapter cannot provide the required semantics, the intent may remain pending and requires an external operational decision.

This is an **active research prototype, not a production certification or independent security audit**.

## Research and archival record

- **Author:** Liran Bar-Shrim
- **Canonical repository:** https://github.com/liranbarshrim-ui/human-stop-boundary
- **Research site:** https://matrix-audit.com
- **Citation metadata:** [`CITATION.cff`](CITATION.cff)
- **Zenodo metadata:** [`.zenodo.json`](.zenodo.json)
- **Provenance policy:** [`PROVENANCE.md`](PROVENANCE.md)
- **Version history:** [`CHANGELOG.md`](CHANGELOG.md)
- **License:** Apache-2.0

The repository is prepared for persistent archiving through GitHub Releases, Zenodo, and Software Heritage. A canonical release must preserve its version, evidence, limitations, and integrity references.

## Read next

1. **[DAR Core Doctrine](dar_v36_14/DAR_DOCTRINE.md)** — the conceptual foundation.
2. **[Implementation README](dar_v36_14/README.md)** — what v36.14 actually enforces.
3. **[Security](dar_v36_14/SECURITY.md)** — boundary conditions and explicit limitations.
4. **[Verification Record](dar_v36_14/AUDIT_v36_14.md)** — findings, corrections, evidence, and claims not established.
5. **[Release SHA-256](dar_v36_14/RELEASE_SHA256.txt)** — release artifact integrity reference.
6. **[Provenance Policy](PROVENANCE.md)** — how DAR evidence and claims are established.
7. **[Changelog](CHANGELOG.md)** — versioned research history and known limitations.

---

**Liran Bar-Shrim**  
https://matrix-audit.com
