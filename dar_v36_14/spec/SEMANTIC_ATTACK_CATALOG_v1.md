# DAR Semantic Attack Catalog v1

These attacks target the formal meaning of the DAR property rather than implementation race conditions.

## S-01 — Journal/World Divergence

**Question:** Can an external protected effect occur before DAR records `COMMITTED`, followed by a crash and later `REFUSED`?

**Failure:** Any claim that `REFUSED` proves external non-occurrence.

**Required defense:** Atomic external transaction, idempotent transactional adapter, or explicitly bounded compensating protocol.

## S-02 — Epoch/Person Substitution

**Question:** Can an epoch transition occur without authenticated evidence that the named human principal issued the refusal?

**Failure:** Treating epoch transition as equivalent to named-human refusal.

**Required defense:** Authenticated refusal record bound to principal and effect.

## S-03 — WRITE/Outcome Substitution

**Question:** Does the A1 audit cover only a local WRITE primitive while the protected effect is a downstream irreversible outcome?

**Failure:** Claiming complete mediation of the outcome from mediation of only one syscall or adapter.

**Required defense:** Audit the complete causal boundary of the declared protected outcome.

## S-04 — Availability/Stop-Latency

**Question:** Can a protected adapter hold the Store lock indefinitely while a valid refusal waits?

**Failure:** Operational STOP guarantee silently interpreted as immediate refusal.

**Required defense:** Explicit latency bound, cancellation protocol, or a design that separates authorization linearization from long-running external IO without reopening the safety race.

## S-05 — Cross-Durability Divergence

**Question:** Can Store, Journal, and external effect reach states that cannot be reconstructed consistently after crash?

**Failure:** Treating local journal convergence as proof of external outcome state.

**Required defense:** Explicit crash-consistency protocol and deployment-specific external-effect semantics.
