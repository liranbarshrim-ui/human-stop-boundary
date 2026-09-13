# Security status

DAR v36.14 is a hardened research prototype, not a production security certification. It does not claim universal control over arbitrary AI systems.

For effects routed through the privileged dispatcher, the prototype enforces capability binding, privileged verification, replay prevention, durable intent, recovery parameter binding, journal transition integrity, fail-closed journal preparation, authoritative COMMITTED status, peer-credential checks and tested filesystem/process hardening.

## Explicit limits

- Anti-rollback requires a trusted monotonic anchor outside the Store rollback domain.
- Exactly-once execution across arbitrary external systems remains adapter-dependent.
- Seccomp is a deny-list, not a complete syscall allow-list.
- Landlock is optional and host-kernel dependent.
- The tests are not an independent security audit or exhaustive crash campaign.
- Stronger identity/attestation, delegation, deployment controls and production-distribution testing remain future work.

For suspected vulnerabilities, use the repository's supported private GitHub security-reporting mechanism rather than publishing exploit details in a public issue.
