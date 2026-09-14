# Changelog

All notable DAR research versions should be recorded here with both changes and known limits.

## v36.15 — 2026-09-14

### Research correction
- Added Boundary Conformance v2 after adversarial review identified two load-bearing conditions that were previously stated as assumptions but could be mistaken for established properties.
- The core claim now explicitly requires **(1) a trusted external monotonic anchor outside the Store rollback domain and (2) an independently established interface-completeness property** for all paths capable of producing the protected effect.
- Added `boundary_manifest_v2.json`, `ASSUMPTIONS_v2.md`, `FORMAL_PROPERTY_v2.md`, and `EMPIRICAL_STATUS_v2.md`.
- Version 1 remains historical; its results are not rewritten.
- Clarified that tests of the registered path are not evidence of system-wide complete mediation and that absence of an external monotonic anchor prevents a PASS for anti-rollback.

### Current status
- v2 core-property validation is **PENDING**, not PASS.
- The existing test suite remains bounded implementation evidence.
- Independent interface/escape audit and deployment-specific rollback validation are still required.

## v36.14 — 2026-09-13

### Research state
- Canonical public research release candidate for the DAR v36.14 implementation.
- Authored and maintained by Liran Bar-Shrim.

### Verification record
- Development checkout: `PYTHONPATH=. pytest -q -v`
- Reported result: **60 passed, 1 skipped (61 collected)**.
- The skipped test is the optional Landlock test when the host kernel returns `ENOSYS`.
- Additional local checks reported in the repository include package installation, Python compilation, live two-UID boundary testing, and live `SIGKILL` generation-rotation testing.

### Known limitations
- DAR does not claim universal control over arbitrary AI systems; claims are bounded to effects routed through the enforcement boundary.
- Anti-rollback requires a trusted monotonic anchor outside the rollback domain.
- Exactly-once semantics for arbitrary external side effects depend on an authoritative idempotent adapter.
- Pending-intent reconciliation can remain pending when deployment dependencies cannot provide the original parameters or required adapter semantics.
- The project is an active research prototype, not a production certification or independent security audit.

### Provenance rule
Chat-pasted artifacts are unverified until compared against a fresh repository checkout and executed.

### Archival metadata
- GitHub repository: https://github.com/liranbarshrim-ui/human-stop-boundary
- Research site: https://matrix-audit.com
- Citation metadata: `CITATION.cff`
- Zenodo metadata: `.zenodo.json`
- License: Apache-2.0
