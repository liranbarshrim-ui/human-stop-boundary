# Independent Reproduction Protocol

The strongest external test of DAR is reproduction by an implementation that does not import DAR's enforcement internals.

## Required inputs

An independent evaluator receives only:

- `boundary_manifest_v1.json`
- `ASSUMPTIONS_v1.md`
- `THREAT_MODEL_v1.md`
- `ATTACK_CATALOG_v1.md`
- `FORMAL_PROPERTY.md`
- `CONFORMANCE.md`

## Prohibited shortcuts

The evaluator should not treat DAR's own implementation as an oracle for whether an attack is in scope, whether refusal was valid, or whether a protected effect committed.

## Required output

The evaluator publishes:

1. implementation identity and commit/version;
2. environment;
3. exact input specification hashes;
4. attack results with PASS/FAIL/OUT-OF-SCOPE/AMBIGUOUS;
5. counterexamples, if any;
6. deviations from the protocol;
7. whether the claimed property was reproduced.

A disagreement is preserved as evidence, not silently reconciled.
