# DAR — Manifund Public Funding Proposal

## Title
**DAR: empirically testing whether human stop authority can remain binding in agentic systems**

## Funding target
**$30,000**

## The problem
AI safety often distinguishes between an instruction to stop and a mechanism that makes stopping structurally binding. DAR studies the gap.

The narrow research question is:

> Within a pre-declared protected-effect boundary, once a valid refusal becomes authoritative, can the controlled process still produce the protected effect through rollback, retry, race, crash recovery, or an alternate path?

## What has already been built
DAR is a public research prototype with:
- explicit protected effects and outcome keys;
- external monotonic-fence semantics;
- durable refusal state in PostgreSQL;
- independently hosted Render black-box authority;
- restart-persistence verification;
- five PostgreSQL crash-boundary scenarios;
- repeated refusal/commit race testing;
- explicit fail-closed handling of UNKNOWN states.

The project also documents what these tests do **not** establish: universal AI safety, independent A1 interface completeness, second-provider independence, or production certification.

## Why fund the next stage
The highest-value next step is independent reproducibility. The project needs a second infrastructure provider, substantially higher concurrency, realistic agentic integrations, and external testers who did not design the implementation.

## Milestones
1. Second-provider deployment and black-box reproduction.
2. 10,000+ concurrency/race trials with machine-readable evidence.
3. Crash/restart/retry testing on both infrastructures.
4. Independent interface/escape audit.
5. At least two external reproductions.
6. Public final evidence matrix including negative results.

## Budget
- $10,000 infrastructure and databases
- $7,000 compute/API/agent environments
- $7,000 external testing and security review
- $3,000 reproducibility and archival work
- $3,000 contingency

## What success means
Success is not defined as obtaining a PASS. If an independent environment produces a counterexample, that counterexample will be published and used to refine or reject the corresponding DAR claim.

## Open research
Repository: https://github.com/liranbarshrim-ui/human-stop-boundary
Research site: https://matrix-audit.com

The work is intended as a public-benefit technical AI-safety project. Funding would be used for concrete research, infrastructure, and independent testing rather than private product development.
