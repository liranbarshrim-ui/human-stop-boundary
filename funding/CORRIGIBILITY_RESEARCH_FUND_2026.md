# DAR — Corrigibility Research Fund 2026 Application

## Project
**Decision Accountability Review (DAR): empirical infrastructure for protected human refusal**

## Applicant
Liran Bar-Shrim

## One-sentence proposal
DAR develops and empirically tests a narrow structural condition for corrigibility: within a declared protected-effect boundary, once a valid human refusal becomes authoritative, the controlled process must be unable to produce that protected effect through rollback, retry, race, crash-recovery, or alternate execution paths.

## Why this is corrigibility research
Corrigibility is often discussed as a behavioral property: an AI should remain responsive to correction. DAR asks a complementary systems question: **what must be true of the enforcement boundary so that a correction remains authoritative when the system is under adversarial pressure?**

DAR does not claim to solve alignment or corrigibility in general. It proposes a falsifiable structural property and an implementation/testing protocol around it.

## Current evidence
The repository contains a research prototype and machine-checked evidence including:

- external monotonic-fence and refusal semantics;
- PostgreSQL-backed authoritative refusal state;
- independently hosted Render black-box verification;
- real Render restart-persistence verification;
- five crash-boundary scenarios, including SIGKILL after external refusal, SIGKILL after external commit, repeated refusal/commit races, fresh-idempotency-key bypass attempts, and torn PostgreSQL transaction rollback;
- explicit disclosure of an earlier evidence-validation failure rather than rewriting history.

The current evidence remains deployment-level and conditional. DAR explicitly does not claim an independent A1 interface-completeness audit, a second-infrastructure validation, or universal AI control.

## Proposed work
1. Run the same black-box protocol against a second infrastructure/provider.
2. Scale concurrent race/load testing substantially beyond the controlled 100-run crash test.
3. Build an independent interface-completeness audit protocol that can be executed by researchers who did not author DAR.
4. Publish reproducible artifacts, attack traces, negative results, and a final evidence matrix.
5. Test whether the DAR property can be applied to realistic agentic systems rather than only the current reference implementation.

## Requested funding
**$30,000**.

## Budget
- $10,000 compute, hosting, databases, and independent infrastructure
- $8,000 security/red-team testing and external review
- $5,000 agent/API access and experimental environments
- $4,000 documentation, reproducibility, and archival infrastructure
- $3,000 contingency

## Success criteria
The project succeeds if independent researchers can reproduce the attack protocol, identify the exact assumptions required for a PASS, and either confirm the conditional property in additional environments or produce a concrete counterexample. A counterexample is considered a valuable research result, not a failed project.

## Open science
All funded research outputs will be open source/open access where legally and technically possible. The canonical repository is:
https://github.com/liranbarshrim-ui/human-stop-boundary

Research site:
https://matrix-audit.com

## Central claim
> Within a pre-declared protected-effect boundary, with a trusted external monotonic anchor and an independently established completeness property for all paths capable of producing the protected effect, a valid refusal must make protected effect commitment unreachable.
