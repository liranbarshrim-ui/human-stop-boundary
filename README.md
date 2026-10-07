# Decision Authority Record (DAR)

**A named-authority governance construct for making stop authority explicit, bounded, and testable.**

Defined by **Liran Bar-Shrim**.

**Naming convention:** DAR means **Decision Authority Record**. The record identifies the named authority responsible for refusing continuation before an irreversible effect. **DAR review / DAR Boundary Audit** describes the review process applied to that record and its enforcement boundary. These terms are intentionally distinct.

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

## External deployment evidence

On 2026-09-15, DAR was tested through a live Make deployment against an external Google Sheets state mutation. The controlled effect was a write to `Evidence!A1`.

The bounded result was independently verified:

- **ALLOW** invoked `google-sheets:updateCell`, which reported `updatedCells: 1` and `updatedRange: Evidence!A1`.
- A separate read-back returned the exact value written by the ALLOW execution.
- **DENY** returned `DENY_BLOCKED` and did **not invoke** the external mutation module; the run recorded zero operations.

This is the first recorded **externally verifiable enforcement demonstration** in this repository: the distinction is not merely an internal return value, because the ALLOW path changed external state and the change was subsequently read back.

Evidence record: [`evidence/EXTERNAL_DEPLOYMENT_PROOF_2026-09-15.md`](evidence/EXTERNAL_DEPLOYMENT_PROOF_2026-09-15.md).

The claim is deliberately bounded. This experiment does **not** prove universal control over arbitrary AI systems, complete mediation of every possible external path, production certification, or a full DAR v3 PASS. Those stronger claims require independent interface/escape-path completeness evidence and the other environmental conditions specified below.

## Boundary Conformance v3

Version 1 and v2 remain historical specifications/results and are not rewritten. **Future strong outcome-fence conformance claims use the frozen v3 evidence package.**

The machine-readable and human-readable specification is under [`dar_v36_14/spec/`](dar_v36_14/spec/):

- [`boundary_manifest_v3.json`](dar_v36_14/spec/boundary_manifest_v3.json) — frozen v3 boundary and required conditions;
- [`ASSUMPTIONS_v2.md`](dar_v36_14/spec/ASSUMPTIONS_v2.md) — environmental trust assumptions;
- [`FORMAL_PROPERTY_v3_OUTCOME_FENCE.md`](dar_v36_14/spec/FORMAL_PROPERTY_v3_OUTCOME_FENCE.md) — v3 outcome-fence property;
- [`THREAT_MODEL_v1.md`](dar_v36_14/spec/THREAT_MODEL_v1.md) — adversary capabilities and attack surface;
- [`ATTACK_CATALOG_v1.md`](dar_v36_14/spec/ATTACK_CATALOG_v1.md) — frozen attack families;
- [`CONFORMANCE.md`](dar_v36_14/spec/CONFORMANCE.md) — PASS / FAIL / OUT-OF-SCOPE / AMBIGUOUS rules;
- [`INDEPENDENT_REPRODUCTION.md`](dar_v36_14/spec/INDEPENDENT_REPRODUCTION.md) — protocol for testing the claim without importing DAR internals.

The v3 property is deliberately narrow:

> **For a frozen deployment satisfying A1, A9, A10, A11, A12 and A13, once an authenticated refusal installs terminal external refusal state for outcome O, no later protected operation may produce O.**

DAR does not establish interface completeness merely by implementing its own enforcement interface. Missing or unverified required conditions are not `PASS`.

## Independent Audit Status

The current frozen evidence package does not claim independent interface completeness.

**A11 — No Alternate Protected Outcome Path: PENDING_INDEPENDENT_AUDIT.**

The repository-authored interface/escape analysis is explicitly classified as `AMBIGUOUS` and is not treated as independent evidence.

The remaining question is deployment-level and adversarial:

> Can any alternate process, IPC path, socket, filesystem path, helper, recovery mechanism, or privileged interface produce the protected outcome without passing through the same authoritative refusal/fence boundary?

A qualifying independent audit may confirm the boundary, identify an alternate path, or leave the condition unresolved. No result will be promoted to `PASS` without corresponding evidence.

## Verification

The verified development checkout was previously executed with:

**`PYTHONPATH=. pytest -q -v` → 60 passed, 1 skipped (61 collected).**

The single skip is the optional Landlock test because the host kernel returns `ENOSYS`.

Additional local checks passed: package installation, Python compilation, live two-UID boundary testing, and live `SIGKILL` generation-rotation testing.

These results are bounded implementation evidence, not independent validation of A1 or A11.

### Five-scenario crash-boundary evidence

The repository now includes a dedicated PostgreSQL crash-boundary test covering five failure windows:

1. crash after external refusal but before local persistence;
2. crash after protected external commit but before local persistence;
3. refusal/commit race, repeated for 100 runs;
4. new idempotency key after crash cannot bypass an existing refusal;
5. torn PostgreSQL transaction write interrupted by `SIGKILL`, followed by rollback verification.

The final machine-validated run was GitHub Actions **run 34868342315**, job **104057736583** (the crash-boundary job). All five scenarios returned `PASS`, the machine-readable aggregate returned `verdict: PASS`, and the evidence artifact was uploaded successfully.

This five-scenario result is **crash/transaction-boundary evidence only**. It does not constitute a production certification, an independent A1/A11 interface-completeness audit, a second-infrastructure validation, an uncontrolled external `SIGKILL` test against the Render service, or a full DAR v3 PASS.

### External PostgreSQL restart persistence

A separate deployment-level black-box test against the independently hosted Render authority, backed by PostgreSQL, verified that a terminal refusal survived a real Render auto-deploy restart and continued to block a protected commit afterward. This is restart-persistence evidence, not an uncontrolled `SIGKILL` claim.

The repository must be treated as the source of truth. Chat-pasted artifacts are not evidence until compared against a fresh checkout and executed.

## Security boundary and limits

DAR does **not** claim universal control over arbitrary AI systems, complete mediation by assertion, or protection against effects outside the declared boundary.

HMAC-authenticated state does not by itself prevent restoration of an older valid snapshot. Anti-rollback requires a trusted monotonic anchor outside the Store rollback domain. A deployment without that anchor cannot claim the v3 anti-rollback property.

Likewise, tests of the registered interface do not prove that no alternate path exists. A11 therefore requires an independent interface/escape audit covering processes, IPC, filesystem, adapters, helpers, and other paths capable of producing the protected effect.

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
- **Project identity:** [`PROJECT_IDENTITY.md`](PROJECT_IDENTITY.md)
- **License history:** [`LICENSE_HISTORY.md`](LICENSE_HISTORY.md)
