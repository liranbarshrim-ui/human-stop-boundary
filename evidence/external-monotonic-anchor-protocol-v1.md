# External Monotonic Anchor Protocol v1

## Status

**DESIGN / NOT PASS**. This document defines the evidence gate; it is not evidence that the gate has been satisfied.

## Purpose

DAR v37 requires an external monotonic anchor for the protected WRITE outcome. A timestamp or append-only audit record alone is insufficient. The anchor must participate in the authorization of the protected commit so that a refusal cannot be bypassed by rollback, replay, or reuse of an older state.

## Required properties

1. **Externality** — the monotonic state is maintained outside the DAR process and outside its local filesystem state.
2. **Monotonicity** — accepted authority state cannot move backward to an earlier epoch/version.
3. **Atomic commit check** — the protected commit is accepted only when the external authority atomically confirms that the requested epoch is still valid and no terminal refusal exists.
4. **Refusal dominance** — once refusal for an outcome is published, a later protected commit for that outcome must be rejected, including with a fresh idempotency key.
5. **Crash/restart persistence** — process restart or local-state loss cannot restore an earlier accepted authority state.
6. **Replay resistance** — a previously valid anchor response cannot be replayed to authorize a later commit after refusal.
7. **Independent verification** — evidence must include an externally verifiable artifact identifying the anchor state and the tested transitions.

## Rekor assessment

Rekor is a strong candidate for **witness/evidence** because its transparency log is append-only and cryptographically verifiable. However, Rekor's documented role is transparency and timestamping; it is not itself the DAR protected-effect serialization authority. Therefore a Rekor entry by itself MUST NOT be counted as satisfying this gate.

The implementation may use Rekor as a witness of anchor transitions, while a separate externally controlled serialization authority performs the decisive atomic refusal/commit exclusion.

## Minimum conformance sequence

For one outcome identifier:

1. establish external epoch `E`;
2. publish a refusal at `E` and obtain externally verifiable evidence;
3. attempt protected commit at `E` with the original idempotency key;
4. attempt protected commit at `E` with a fresh idempotency key;
5. attempt commit using a previously captured pre-refusal authorization response;
6. restart/recreate the DAR process and repeat steps 3-5;
7. verify all protected commit attempts are rejected;
8. verify the external state remains at or beyond the refusal state and cannot be rolled back by local state restoration;
9. publish a machine-readable evidence artifact and independent verification reference.

## PASS rule

This protocol is **PASS** only when the decisive external serialization authority and the rollback/replay tests are demonstrated against a real deployed service. Documentation, local mocks, timestamps, or repository-authored assertions alone are insufficient.
