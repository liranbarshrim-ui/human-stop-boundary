# Security status

DAR v36.14 is a hardened research prototype, not a production security certification. It does not claim universal control over arbitrary AI systems.

For effects routed through the privileged dispatcher, the prototype enforces capability binding, privileged verification, replay prevention, durable intent, recovery parameter binding, journal transition integrity, fail-closed journal preparation, authoritative COMMITTED status, peer-credential checks and tested filesystem/process hardening.

## Explicit limits

- Anti-rollback requires a trusted monotonic anchor outside the Store rollback domain. The Store version advances on effect-state mutations as well as authority mutations, so rollback of consumed/pending effect state is detectable when all production writes use the Store path. A second ordinary file on the same attacker-controlled filesystem is not sufficient.
- Exactly-once execution across arbitrary external systems remains adapter-dependent. Pending intents have an explicit reconciliation path, but deployment must supply the original parameters to that path.
- Seccomp is a deny-list, not a complete syscall allow-list.
- Landlock is optional and host-kernel dependent.
- The tests are not an independent security audit or exhaustive crash campaign.
- Stronger identity/attestation, delegation, deployment controls and production-distribution testing remain future work.

For suspected vulnerabilities, use the repository's supported private GitHub security-reporting mechanism rather than publishing exploit details in a public issue.
