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

## Boundary Conformance v2

Version 1 remains the historical preregistration and its results are not rewritten. Future conformance claims use v2, which makes the two load-bearing environmental conditions explicit before a PASS can be claimed.

The machine-readable and human-readable specification is under [`dar_v36_14/spec/`](dar_v36_14/spec/):

- `boundary_manifest_v2.json` — requires an external monotonic anchor and independent interface-completeness audit;
- `ASSUMPTIONS_v2.md` — separates implementation properties from environmental trust conditions;
- `FORMAL_PROPERTY_v2.md` — defines the conditional property and counterexample criterion;
- `EMPIRICAL_STATUS_v2.md` — records the evidence still required before a v2 PASS;
- `THREAT_MODEL_v1.md` — adversary capabilities and attack surface;
- `ATTACK_CATALOG_v1.md` — frozen attack families;
- `CONFORMANCE.md` — PASS / FAIL / OUT-OF-SCOPE / AMBIGUOUS rules;
- `INDEPENDENT_REPRODUCTION.md` — protocol for testing the claim without importing DAR internals.

The revised central claim is deliberately narrow:

> **Within a pre-declared protected-effect boundary, with a trusted external monotonic anchor and an independently established completeness property for all paths capable of producing the protected effect, a valid refusal must make protected effect commitment unreachable.**

DAR does not establish either the monotonic anchor or interface completeness merely by implementing its own enforcement interface. Missing or unverified required conditions are not `PASS`.

## Verification

The verified development checkout was previously executed with:

**`PYTHONPATH=. pytest -q -v` → 60 passed, 1 skipped (61 collected).**

The single skip is the optional Landlock test because the host kernel returns `ENOSYS`.

Additional local checks passed: package installation, Python compilation, live two-UID boundary testing, and live `SIGKILL` generation-rotation testing.

These results are bounded implementation evidence, not independent validation of A1 or A9.

The repository must be treated as the source of truth. Chat-pasted artifacts are not evidence until compared against a fresh checkout and executed.

## Security boundary and limits

DAR does **not** claim universal control over arbitrary AI systems, complete mediation by assertion, or protection against effects outside the declared boundary.

HMAC-authenticated state does not by itself prevent restoration of an older valid snapshot. Anti-rollback requires a trusted monotonic anchor outside the Store rollback domain. A deployment without that anchor cannot claim the v2 anti-rollback property.

Likewise, tests of the registered interface do not prove that no alternate path exists. A1 therefore requires an independent interface/escape audit covering processes, IPC, filesystem, adapters, helpers, and other paths capable of producing the protected effect.

Exactly-once semantics for arbitrary external side effects remain dependent on an authoritative idempotent adapter.

Pending-intent reconciliation is bounded and deployment-dependent: `reconcile_pending()` requires an external `params_provider` to supply the original parameters, verifies their `params_digest`, consults authoritative adapter status, and retries UNKNOWN/PREPARED only through the adapter's idempotent contract. It clears the pending intent only after COMMITTED is established and the journal contains matching validated intent. If the deployment cannot supply the original parameters or the adapter cannot provide the required semantics, the intent may remain pending and requires an external operational decision.

This is an **active research prototype, not a production certification or independent security audit**.

## Research and archival record

- **Author:** Liran Bar-Shrim
- **Canonical repository:** https://github.com/liranbarshrim-ui/human-stop-boundary
- **Research site:** https://matrix-audit.com
- **Citation metadata:** [`CITATION.cff`](CITATION.cff)
- **Archival plan:** [`ARCHIVAL.md`](ARCHIVAL.md)
- **Provenance:** [`PROVENANCE.md`](PROVENANCE.md)
