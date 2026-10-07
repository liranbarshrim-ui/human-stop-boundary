# Independent Reproduction Protocol

The strongest external test of DAR is reproduction against the frozen v3 evidence package by an evaluator that does not import DAR's enforcement internals.

## Quickstart

The following is the intended first-pass path for an independent evaluator working from a fresh checkout.

### 1. Clone the repository

```bash
git clone https://github.com/liranbarshrim-ui/human-stop-boundary.git
cd human-stop-boundary
```

For a reproducible review, record the exact commit before running anything:

```bash
git rev-parse HEAD
git status --short
```

Do not modify the working tree before recording the starting commit. The evaluator should report that commit/version with the findings.

### 2. Install the project

Use the repository's documented test/development installation path for the current checkout. The baseline verification command is:

```bash
PYTHONPATH=. pytest -q -v
```

If the environment requires additional setup, record the exact commands, versions, operating system, kernel, Python version, and any skipped or unavailable hardening features.

### 3. Establish the baseline before attacking

Run the baseline suite first and preserve the output. Do not treat a passing baseline as evidence that the security property holds.

The independent evaluator should then proceed to the frozen v3 threat model and attack catalog rather than using DAR's implementation as an oracle.

## Frozen specification inputs

The independent evaluator should use the following repository files as the pre-registered specification:

- `dar_v36_14/spec/boundary_manifest_v3.json`
- `dar_v36_14/spec/ASSUMPTIONS_v2.md`
- `dar_v36_14/spec/THREAT_MODEL_v1.md`
- `dar_v36_14/spec/ATTACK_CATALOG_v1.md`
- `dar_v36_14/spec/FORMAL_PROPERTY_v3_OUTCOME_FENCE.md`
- `dar_v36_14/spec/CONFORMANCE.md`

## Required inputs

An independent evaluator receives the frozen v3 evidence package and should establish its own environment and attack results rather than importing DAR's enforcement internals.

## Prohibited shortcuts

The evaluator should not treat DAR's own implementation as an oracle for whether an attack is in scope, whether refusal was valid, or whether a protected effect committed.

In particular, a repository test that passes is not independent evidence that no alternate protected path exists.

## Required attack focus

At minimum, the evaluation should attempt to falsify:

1. alternate process / IPC / socket / filesystem / helper paths to the protected effect;
2. capability replay, stale-generation use, and authority confusion;
3. crash/recovery paths and durable-intent transitions;
4. adapter idempotency and `COMMITTED` semantics;
5. rollback and monotonic-anchor assumptions;
6. discrepancies between the declared boundary and the actual deployment/effect universe.

## Required output

The evaluator publishes:

1. implementation/deployment identity and commit/version;
2. environment;
3. exact input specification hashes;
4. attack results with PASS/FAIL/OUT-OF-SCOPE/AMBIGUOUS;
5. counterexamples, if any;
6. deviations from the protocol;
7. whether the claimed property was reproduced.

A disagreement is preserved as evidence, not silently reconciled.

## Version discipline

The evaluator should record the exact commit tested. If the repository changes during the review, those changes constitute a different review target unless the evaluator explicitly elects to update the tested commit and records the transition.

The author grants explicit written permission for independent evaluators to clone, run, modify, instrument, fuzz, red-team, and publish findings, including negative findings, for evaluation purposes. This permission does not convert the repository's proprietary license into a general open-source license; it is a specific evaluation and publication permission.

## Reporting

Negative findings are explicitly welcome. A counterexample, an unresolved assumption, or a recommendation to narrow the security claim is a valid and useful outcome.
