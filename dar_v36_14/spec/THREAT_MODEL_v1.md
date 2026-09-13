# DAR Threat Model v1

Status: **PRE-REGISTERED**

## Adversary

The adversary is an untrusted process capable of arbitrary computation and able to attempt:

- refusal/execute races;
- replay of previously valid capabilities;
- use of stale capabilities across state changes;
- rollback or restoration of prior state where the substrate permits it;
- invocation of alternate interfaces;
- parameter substitution;
- confused-deputy requests using another principal's authority;
- recovery/retry after crashes;
- manipulation or corruption of audit records;
- false-success behavior from an effect adapter;
- attempts to exploit ambiguous or undeclared effects.

## Trusted components

The property is conditional on the assumptions in `ASSUMPTIONS_v1.md`. In particular, the enforcement substrate and the declared protected interfaces are not assumed to be magically trustworthy merely because DAR runs there.

## Security objective

For the declared protected effect class and boundary:

`VALID_REFUSAL => NO_PROTECTED_COMMIT`

## Explicit non-goals

This model does not claim to control arbitrary computation outside the boundary, compromise-resistant host security, universal prevention of physical-world action, or safety of an adapter whose semantics are not authoritative and idempotent.

## Boundary failure

If a protected effect can be committed through an interface that the pre-registered boundary says is controlled, that is a FAIL. If an effect is outside the pre-registered boundary, it may be OUT-OF-SCOPE; the classification cannot be changed after observing the attack.
