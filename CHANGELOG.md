# Changelog

All notable DAR research versions should be recorded here with both changes and known limits.

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
