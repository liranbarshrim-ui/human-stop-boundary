# DAR — Foresight AI for Science & Safety Nodes RFP

## Focus area
**II. Coordination and accountability**

## Project
**Decision Accountability Review (DAR): an independent, testable accountability layer for agentic systems**

## Applicant
Liran Bar-Shrim

## Executive summary
As AI systems become more agentic, human oversight is not enough if the system being governed can redefine or bypass the mechanism by which a stop decision becomes binding. DAR is an open framework for testing a narrower question: **after a valid stop/refusal becomes authoritative for a protected effect, can the controlled process still produce that effect through another route?**

DAR converts this into explicit assumptions, a machine-readable property, an attack catalog, and black-box deployment tests.

## Why this fits the RFP
DAR directly targets coordination and accountability: independent institutions need ways to evaluate whether nominal human authority is actually structurally binding in AI-mediated systems. The framework is intentionally designed to produce evidence and counterexamples rather than trust claims.

## Existing work
The public repository contains:
- the DAR doctrine and narrow formal property;
- external-fence/refusal implementation;
- PostgreSQL authoritative state;
- independently hosted Render authority;
- restart-persistence evidence;
- five crash-boundary scenarios including SIGKILL and torn transaction rollback;
- concurrency and black-box load experiments;
- explicit limitations and preserved failed-run history.

## 12-month plan
**Phase 1:** second-infrastructure reproduction and hardened deployment harness.

**Phase 2:** high-concurrency and adversarial agent experiments, including realistic agent/API workflows.

**Phase 3:** independent interface-completeness audit and external red-team reproduction.

**Phase 4:** comparative study across infrastructures and publication of a final DAR evidence standard.

## Requested support
**$60,000**, with preference for grant + compute/infrastructure support.

Budget:
- $18,000 infrastructure, databases, compute, and API access
- $15,000 independent security/red-team testing
- $12,000 agentic-system integration experiments
- $8,000 reproducibility, documentation, and archival work
- $7,000 contingency/overhead

## Deliverables
1. Open-source second-provider reference deployment.
2. Public attack/evidence corpus.
3. Independent reproduction protocol.
4. Agentic-system case studies.
5. Final report distinguishing demonstrated properties, assumptions, ambiguities, and counterexamples.

## Open-source commitment
The funded work product will be open sourced, subject to ordinary security disclosure constraints.

Repository: https://github.com/liranbarshrim-ui/human-stop-boundary
Research site: https://matrix-audit.com

## Limits
DAR does not claim universal AI control, universal alignment, or production certification. A PASS is conditional on declared boundary coverage, external monotonic anchoring, and independent completeness evidence. Missing conditions are not silently treated as PASS.
