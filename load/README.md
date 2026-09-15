# DAR 10K Cross-Engine Load Strategy

This directory separates three claims that must not be conflated:

1. **Canonical 10K correctness** — exactly 10,000 DAR rounds complete with zero infrastructure failures and zero invariant failures.
2. **Distributed 10K execution** — the same black-box contract is exercised across independent load-generator shards.
3. **10K concurrency stress** — a separate performance experiment that increases simultaneous VUs/users; it is not itself evidence of 10,000 correct DAR decisions.

## Canonical authority gate

Before any load test, `/health` must return HTTP 200 with `ok=true` and `persistence=postgres`. A 502/503/504, timeout, transport failure, or non-Postgres readiness state is **INCONCLUSIVE**, never PASS.

The current external-load harness already follows this principle: its workflow explicitly requires 10,000 rounds, 32 workers, and all checks PASS before the evidence can be accepted. See `.github/workflows/external-load-stress.yml`.

## k6 — primary load engine

`load/k6/dar_10k.js` is the canonical high-concurrency implementation. It uses k6's `http.batch()` for the refuse/fence race, then verifies state and tests that a fresh idempotency key cannot bypass a refusal.

Local:

```bash
DAR_AUTHORITY_URL=https://dar-external-authority-v2.onrender.com \
DAR_LOAD_ROUNDS=10000 DAR_LOAD_VUS=32 \
k6 run load/k6/dar_10k.js
```

The GitHub workflow `.github/workflows/dar-10k-k6.yml` is deliberately **manual** (`workflow_dispatch`) so a broken authority cannot accidentally consume a run. It performs a database-backed preflight and then requires an evidence verdict of PASS.

For larger distributed tests, Grafana documents both execution segments and Kubernetes k6 Operator. Grafana also notes that a single optimized k6 machine can already generate very large loads, so distributed execution should be used when multiple source IPs/locations or generator capacity are actually required.

## Locust — independent cross-engine implementation

`load/locust/locustfile.py` is a secondary implementation. It supports deterministic sharding with:

```text
DAR_SHARD_INDEX=0..N-1
DAR_SHARD_COUNT=N
```

The workflow creates ten 1,000-round shards and aggregates their evidence. This is intentionally independent from k6, so a PASS from both engines is stronger than a PASS from a single runner.

## Evidence contract

A valid PASS requires:

```text
completed_rounds == 10000
infrastructure_failures == 0
invariant_failures == 0
verdict == PASS
```

The evidence must also identify the authority URL, test engine, seed, VU/worker configuration, and Git commit used to produce it.

## Recommended execution order

```text
1. Repair/verify PostgreSQL-backed authority
2. Single-round smoke test
3. 100-round controlled test
4. Canonical 10K with k6
5. Distributed 10K with Locust
6. Independent cloud stress test (k6 Cloud / AWS distributed load testing)
7. Anchor final evidence externally
```

Do not call a run PASS merely because a CI job or deployment says SUCCESS. The evidence artifact itself is the acceptance gate.
