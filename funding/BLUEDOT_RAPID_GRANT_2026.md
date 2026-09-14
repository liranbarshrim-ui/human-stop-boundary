# DAR — BlueDot Rapid Grant Application

## Project
**Black-box stress testing of protected refusal in AI-agent control boundaries**

## Request
**$10,000**

## The work
DAR is an open research prototype testing one narrow AI-safety property: after an authoritative refusal, can the protected outcome still happen through race conditions, retries, rollback, crashes, restart, or alternate paths?

The current implementation already has external PostgreSQL persistence, an independently hosted Render authority, and five crash-boundary tests. The next bottleneck is broader empirical testing rather than basic implementation.

## What the grant buys
- second-provider infrastructure and database
- high-concurrency load testing
- agent/API access for realistic protected outcomes
- external red-team/reproduction support
- reproducible evidence and public artifacts

## Milestones
**M1 — Second infrastructure:** deploy the same authority semantics independently and reproduce the black-box refusal/fence tests.

**M2 — Concurrency:** run high-volume refusal/commit races under real HTTP load and record all ambiguous/error states rather than treating them as PASS.

**M3 — Crash matrix:** reproduce the five crash windows on the second infrastructure and compare behavior.

**M4 — Independent reproduction:** provide a protocol that an external tester can execute without relying on DAR implementation internals.

**M5 — Publication:** release results, failures, attack traces, and a final evidence matrix.

## Why now
The project is beyond the purely conceptual stage. The limiting resource is now independent infrastructure and adversarial testing. A small rapid grant can directly convert an existing prototype into stronger externally reproducible evidence.

## What DAR does not claim
DAR is not presented as a universal AI-safety solution, an alignment proof, or a production security certification. Its claim is deliberately narrower and falsifiable.

## Core property
> Within a declared protected-effect boundary, once a valid refusal is authoritative, protected effect commitment must be unreachable through the tested attack surfaces.

## Outputs
All code, test protocols, evidence schemas, and negative results will be published openly.

Repository: https://github.com/liranbarshrim-ui/human-stop-boundary

Research site: https://matrix-audit.com
