# DAR Funding Application Package — 2026

**Applicant:** Liran Bar-Shrim  
**Project:** Decision Accountability Review (DAR)  
**Repository:** https://github.com/liranbarshrim-ui/human-stop-boundary  
**Research site:** https://matrix-audit.com

## 1. One-sentence project description

DAR is an empirically testable framework for determining whether a designated human stop/refusal remains structurally authoritative against bypass, rollback, race, retry, crash, and alternate-path attacks within a declared protected-effect boundary.

## 2. The narrow claim

> Within a pre-declared protected-effect boundary, with a trusted external monotonic anchor and an independently established completeness property for all paths capable of producing the protected effect, a valid refusal must make protected-effect commitment unreachable.

DAR does **not** claim to solve AI alignment, AI safety, or control in general. It tests a narrower structural question: whether a stop condition remains binding when the system, process, or authority structure is subjected to adversarial pressure.

## 3. Why this matters

As AI systems become more agentic, a human instruction to stop is useful only if the architecture makes that decision authoritative. A policy saying “stop” is different from an enforcement boundary in which the protected outcome becomes unreachable after the refusal is committed.

DAR therefore treats stop authority as an engineering property that can be specified, attacked, and empirically tested.

## 4. Current evidence

The repository contains implementation and empirical evidence covering:

- protected outcome fencing and refusal semantics;
- external monotonic-anchor requirements for anti-rollback;
- atomic serialization of refusal and protected commit;
- idempotency and retry behavior;
- Unicode canonicalization and effect/outcome identity binding;
- process-isolated HTTP authority testing;
- independently hosted Render black-box authority testing;
- PostgreSQL-backed restart-persistence verification after a real Render auto-deploy restart;
- five crash-boundary scenarios using real PostgreSQL and SIGKILL, including a torn transaction write;
- repeated refusal/commit race testing;
- explicit disclosure of a preceding evidence-validation failure rather than rewriting history.

### Five-scenario crash-boundary evidence

GitHub Actions run **34868342315**, job **104057736583**, machine-validated all five scenarios as PASS:

1. crash after external refusal before local persistence;
2. crash after external protected commit before local persistence;
3. refusal/commit race across 100 runs;
4. new idempotency key after crash cannot bypass refusal;
5. torn PostgreSQL transaction interrupted by SIGKILL rolls back rather than exposing partial state.

The immediately preceding run **34868180786** executed the five scenarios but failed the evidence-validation step because the evidence file was not in the expected machine-readable form. The corrected run passed, and the earlier failure remains visible in Actions history.

### External restart persistence

A separate black-box workflow verified that a terminal refusal survived a real Render auto-deploy restart of the independently hosted PostgreSQL-backed authority and continued to block a protected commit afterward. This is deployment-level restart evidence, not an uncontrolled SIGKILL test against Render and not a production certification.

## 5. What remains unproven

DAR deliberately does not present the following as established:

- independent A1 interface-completeness/escape-path audit;
- second independent infrastructure/provider validation;
- uncontrolled external SIGKILL of the hosted Render service;
- production certification;
- universal AI-safety or alignment claims;
- completion of the current external concurrent-load experiment until its final machine-readable result is available.

These limitations are part of the research claim, not hidden qualifications.

## 6. Proposed funded work

Funding would be used for a focused empirical validation program:

1. **Second-infrastructure replication** — reproduce the external authority and crash-boundary evidence on a materially different hosting/database stack.
2. **High-concurrency black-box testing** — increase concurrent load and duration against an externally hosted authority, recording both semantic safety invariants and infrastructure saturation separately.
3. **Independent interface audit** — have an external reviewer attempt to enumerate every path capable of producing the protected outcome and search for an unmediated escape path.
4. **Adversarial red-team protocol** — provide an evaluator with the public claim and deployment interface without internal implementation details, then record attempted bypasses and counterexamples.
5. **Reproducible publication** — freeze specifications, attack catalogues, evidence artifacts, and machine-readable verdicts so independent researchers can reproduce or falsify the claim.

## 7. Deliverables

- second-provider deployment and reproducibility report;
- concurrency/load evidence with machine-readable artifacts;
- independent interface/escape audit report;
- blind red-team report;
- updated formal specification and threat model;
- public evidence index linking each claim to a reproducible test;
- explicit PASS / FAIL / AMBIGUOUS classification with no unsupported PASS claims.

## 8. Funding request — Corrigibility Research Fund

**Requested:** $30,000.

**Use:** independent audit and replication, external hosting/database costs, sustained concurrency testing, adversarial evaluation, and reproducible evidence publication.

**Fit:** DAR operationalizes a narrow aspect of corrigibility: preserving meaningful human control after a valid correction/refusal rather than relying on the controlled agent to voluntarily comply.

## 9. Funding request — Manifund

**Requested target:** $30,000.

**Milestone structure:**

- $7,500 — second-infrastructure replication;
- $7,500 — high-concurrency black-box testing;
- $7,500 — independent interface and adversarial review;
- $7,500 — final reproducibility package and publication.

Funding can be adjusted according to donor interest and project milestones.

## 10. Funding request — BlueDot Rapid Grant

**Requested:** $10,000.

**Immediate use:** compute/API credits, independent hosting/database costs, load-testing infrastructure, and external evaluation needed to turn the existing deployment evidence into a broader reproducibility package.

The request is intentionally concrete: money is a bottleneck for running the next empirical validation layer, not for general productivity or living expenses.

## 11. Funding request — Foresight AI for Science & Safety Nodes

**Requested:** $35,000–$50,000 depending on program fit.

**Proposed framing:** DAR as an independent technical accountability layer for increasingly agentic systems. The project focuses on when human control is genuinely binding, how to detect hollow oversight, and how independent technical assessment can create a middle layer between AI labs, operators, and public governance.

## 12. What success would mean

Success is not “DAR proved AI safety.”

Success is a progressively stronger empirical answer to a narrower question:

> Can an independently specified and externally tested boundary make a protected outcome unreachable after a valid human refusal, even under rollback, retry, crash, race, persistence, and alternate-path attacks?

A counterexample would be valuable too. If an independent evaluator finds a bypass, DAR will record it as a failure and revise the framework rather than redefine the claim.

## 13. Contact / submission note

This package is intended to be adapted to each funder's application form. It should not be represented as a submitted application until the applicant has personally completed any required identity, legal, tax, banking, or grant-agreement steps.
