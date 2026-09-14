# DAR Refusal Protocol v1

## Status

**SPECIFICATION / IMPLEMENTATION PENDING**

This document separates an authenticated named-human refusal from the epoch barrier that implements capability invalidation.

## Required refusal record

A refusal record MUST bind:

- `refusal_id`
- `principal_id`
- `principal_authentication`
- `effect_id`
- `effect_class`
- `target_epoch`
- `issued_at`
- `accepted_at`
- `signature_or_attestation`

The exact authentication mechanism is deployment-specific and MUST be declared in the deployment manifest.

## Required ordering

The refusal protocol MUST establish a durable ordering:

```text
authenticated refusal
    -> durable refusal acceptance
    -> refusal state transition / epoch advance
    -> invalidation of affected capabilities
```

A raw Store write that increments `epoch` does not satisfy this protocol.

## Recovery

A recovery implementation MUST preserve the distinction between:

1. a refusal that was authenticated and accepted;
2. an epoch barrier produced by that refusal;
3. evidence that an external protected effect did or did not occur.

Recovery MUST NOT infer (1) from (2), and MUST NOT infer non-occurrence of (3) from a `REFUSED` journal record.

## Implementation status

The current v36.14 implementation provides an epoch barrier but does not yet implement the complete authenticated named-human refusal protocol specified here.

Therefore A human-authority claim remains **PENDING** until an implementation and corresponding tests establish this protocol.
