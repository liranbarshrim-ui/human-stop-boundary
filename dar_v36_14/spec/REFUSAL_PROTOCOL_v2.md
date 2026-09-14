# DAR Refusal Protocol v2

Status: SPECIFICATION / IMPLEMENTATION PENDING

## Purpose

DAR distinguishes an authenticated human refusal from the epoch transition that enforces it.

An epoch change is not itself evidence that a named human said NO.

## RefusalIntent

A valid refusal is an authenticated, authorized refusal against a specific protected-effect instance.

Conceptual fields:

- `refusal_id`: unique refusal event identifier.
- `principal`: stable identifier of the authorized human principal.
- `principal_authentication`: evidence that the principal authenticated to the refusal interface.
- `effect_id`: the protected effect instance being refused.
- `target_epoch`: the epoch in which the refusal takes effect.
- `issued_at`: timestamp or monotonic ordering evidence where available.
- `signature`: cryptographic authentication evidence when the deployment supports signed refusals.

The implementation MUST NOT infer the identity of the refusing human merely from an epoch increment.

## Enforcement ordering

The intended ordering is:

`authenticated human refusal -> durable refusal record -> epoch transition -> invalidation of affected capabilities`

A deployment MAY implement the authenticated refusal interface differently, but it MUST provide independently auditable evidence connecting the authorized principal to the refusal event.

## Formal validity

A refusal is `valid_refusal(r,e)` only if:

1. `r` identifies an authorized principal;
2. the principal authentication is accepted by the declared refusal authority;
3. `r` identifies the protected effect instance `e`;
4. the refusal is durably ordered before any protected commit for `e`;
5. the enforcement boundary accepts the refusal and applies its invalidation semantics.

An epoch transition without these conditions is an internal state transition, not a demonstrated human refusal.

## Current implementation status

The existing prototype uses epoch invalidation as its enforcement primitive. It does not yet implement all fields or establish a cryptographically bound named-human refusal object. Therefore the full named-human refusal claim remains PENDING.

## Non-claims

This protocol does not establish:

- that a human cannot be impersonated outside the declared authentication boundary;
- that an external side effect can be undone after a crash;
- that an epoch barrier protects effects outside the declared protected-effect boundary;
- that a refusal is operationally immediate while an external adapter is executing.
