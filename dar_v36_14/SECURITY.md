# Security status

DAR v36.14 is a hardened research prototype, not a production security certification. It does not claim universal control over arbitrary AI systems.

For effects routed through the privileged dispatcher, the prototype enforces capability binding, privileged verification, replay prevention, durable intent, recovery parameter binding, journal transition integrity, fail-closed journal preparation, authoritative COMMITTED status, peer-credential checks and tested filesystem/process hardening.

## Explicit limits

- **Bounded enforcement:** DAR's claims apply only to effects actually routed through the controlled enforcement boundary. It cannot structurally stop an effect that bypasses that boundary.
- **Anti-rollback:** the Store is HMAC-authenticated, but HMAC does not prevent restoration of an older valid snapshot. Rollback protection requires a trusted monotonic anchor outside the Store rollback domain. The Store version advances on effect-state mutations as well as authority mutations, so rollback of consumed/pending effect state is detectable when all production writes use the Store path. A second ordinary file on the same attacker-controlled filesystem is not sufficient.
- **Exactly-once:** execution across arbitrary external systems remains adapter-dependent. The adapter must provide an idempotency key and authoritative status. DAR records `COMMITTED` only after that status is confirmed.
- **Pending recovery:** `reconcile_pending()` is a bounded post-success reconciliation mechanism. It can clear a durable intent after authoritative external commitment is established and the journal state is validated. It does not retain the original effect parameters and does not autonomously retry an UNKNOWN/PREPARED effect. Such an intent may remain pending indefinitely and requires an external operational recovery decision if it never reaches COMMITTED.
- **Linux hardening:** seccomp is a deny-list, not a complete syscall allow-list. Landlock is optional and host-kernel dependent.
- **Testing scope:** the tests are not an independent security audit or exhaustive crash campaign.
- **Deployment scope:** stronger identity/attestation, delegation, deployment controls and production-distribution testing remain future work.

## Evidence provenance

A claim is supported only by the artifact that was actually inspected and executed. Chat-pasted files, snippets or remembered versions are unverified until compared against a fresh repository checkout.

The intended evidence chain is:

**artifact → fresh checkout → exact comparison → execution → observed result → bounded claim**

This prevents pasted-artifact drift from turning a result from one version into a claim about another.

For suspected vulnerabilities, use the repository's supported private GitHub security-reporting mechanism rather than publishing exploit details in a public issue.
