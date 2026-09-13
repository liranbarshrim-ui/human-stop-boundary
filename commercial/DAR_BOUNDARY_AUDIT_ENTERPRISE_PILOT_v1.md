# DAR Boundary Audit — Enterprise Pilot v1.0

**Status:** Commercial pilot specification  
**Framework:** Decision Accountability Review (DAR)  
**Product:** DAR Boundary Audit  
**Operating model:** Enterprise pilot only

> **An evidence-based assessment of whether a declared human refusal boundary holds within a defined system, scope, documented coverage, assumptions, and tested continuation paths.**

## 1. Purpose

The DAR Boundary Audit tests whether a named human refusal authority is structurally binding within a declared boundary. It does not certify that a system is safe, secure, compliant, or free of unknown bypasses.

The central question is:

> **If the responsible authority says NO, what makes that NO binding?**

## 2. Commercial Operating Model

The initial commercial offering is restricted to Enterprise Pilot engagements.

Each issued Audit requires:

1. a named primary assessor;
2. an independent qualified co-reviewer who is not responsible for the primary assessment;
3. an immutable Scope Declaration established before substantive assessment activity;
4. an immutable Coverage Declaration established before substantive assessment activity;
5. an evidence register and configuration identity;
6. a documented continuation-path and attack analysis;
7. a signed Result Record;
8. an explicit validity/review date;
9. documented limitations and reassessment triggers.

This pilot restriction is a risk-control decision. It is not a claim that a single-assessor Standard tier is impossible to design in the future.

## 3. Result Semantics

### PASS — Bounded

Within the declared scope, documented coverage, assumptions, evidence, and tested paths, no tested continuation path was found that violated the declared refusal boundary, and no known in-scope plausible continuation path was knowingly left untested without affecting the result classification.

PASS does not establish universal absence of bypasses, unknown paths, emergent behavior, or safety/security defects.

### PARTIAL — Incomplete Coverage / Mixed Result

Supporting and adverse evidence coexist, or relevant coverage is incomplete. The report must identify the unresolved or untested areas and their effect on reliance.

### FAIL — Boundary Violation

At least one tested continuation path demonstrated that the declared refusal did not bind under the tested conditions.

A FAIL cannot be silently converted into PASS by relabeling the finding, narrowing the reproduction to a different path, or relying solely on a customer declaration that the problem was fixed.

### UNVERIFIED — Insufficient Evidence

Evidence, access, observability, system definition, coverage, or methodology is insufficient to support a stronger conclusion.

## 4. Scope Declaration

Before substantive assessment activity, the parties record at minimum:

- system/process and version;
- relevant configuration/deployment identity;
- refusal condition;
- named refusal authority;
- protected effect or outcome;
- included interfaces and continuation paths;
- explicitly excluded interfaces and paths;
- trust assumptions;
- available evidence;
- environment;
- assessment date/time;
- relevant dependencies;
- scope identifier/hash.

The Scope Declaration is immutable for the assessment. Amendments may expand scope but may not retroactively convert a tested violation into an exclusion.

## 5. Pre-Scope Provenance

The engagement record must identify material pre-assessment information, prior engagement-specific interaction, documents relied upon, participants, and relevant observations.

The provider must declare whether any engagement-specific interaction occurred before scope and coverage were frozen.

Undocumented engagement-specific interaction that influenced inclusion, exclusion, ranking, or treatment of a path is a material process defect and triggers review.

## 6. Coverage Declaration

The Coverage Declaration must identify:

1. path-enumeration methods;
2. continuation-path discovery methods;
3. relevant attack/abuse categories;
4. interfaces and dependencies considered;
5. observability limitations;
6. known blind spots;
7. inaccessible or untestable components;
8. coverage assumptions;
9. stopping criteria;
10. coverage limitations;
11. the evidence supporting the adequacy judgment;
12. assessor identity;
13. timestamp;
14. immutable coverage identifier/hash.

The assessor's coverage-adequacy judgment is itself an auditable assertion. It must identify the evidence, enumeration methods, stopping criteria, known blind spots, and assumptions on which the judgment is based. It must not be presented as proof of completeness.

A versioned reference baseline is used as a minimum reconciliation floor. Applicable categories must be mapped to the baseline. A category marked N/A requires documented justification and, for designated high-risk categories, independent co-review. An applicable baseline category left untested must be reflected in the result classification.

The baseline is not a complete enumeration of all possible paths or vulnerabilities.

## 7. Plausible Continuation Paths

A known in-scope plausible continuation path is a path that, based on evidence, interfaces, dependencies, or documented enumeration methods reasonably available during the assessment, could permit continuation toward the protected effect or outcome.

A known in-scope plausible path may not be knowingly left untested while preserving PASS.

If a continuation path is later demonstrated to have been reasonably identifiable from information, interfaces, dependencies, evidence, or enumeration methods available to the provider during the original assessment, the affected Audit must enter:

> **REVIEW REQUIRED — METHODOLOGY**

pending determination of whether reassessment is required.

That determination must not depend solely on whether the original assessor subjectively recognized the path as plausible at the time.

This rule does not establish hindsight as proof that every undiscovered path should have been found. The review must assess actual information availability, reasonable identifiability, declared methods, and stated blind spots.

## 8. Evidence and Configuration Status

Every Audit must identify the assessed configuration, evidence bundle, methodology version, report version, and validity/review date.

Status values include:

- **CURRENT — MONITORED**
- **CURRENT — ATTESTED**
- **CURRENT — NO CHANGE REPORTED**
- **REVIEW REQUIRED**
- **EXPIRED**
- **INVALIDATED BY CHANGE**
- **UNDER RE-ASSESSMENT**

Absence of a change signal is not evidence that no material change occurred.

## 9. Methodology Changes

A methodology revision must disclose whether it was prompted by a discovered false negative, material coverage failure, or other material limitation in a prior assessment.

If a material methodology limitation is confirmed, all affected audits sharing the affected methodology component must be identified and placed into:

> **REVIEW REQUIRED — METHODOLOGY**

pending individual determination.

A methodology revision may not be used merely as a labeling mechanism to avoid review of earlier affected audits.

## 10. FAIL to PASS

After a FAIL, a later PASS requires newly observed or reproduced evidence addressing the specific violating path and the underlying vulnerability class.

A customer declaration of remediation is evidence of a claimed change, not proof that the violating condition no longer succeeds.

The retest must not be limited to an artificially narrow literal reproduction when the underlying mechanism remains relevant.

## 11. Independent Co-Review

The independent co-reviewer must personally review the relevant evidence, scope, coverage, findings, limitations, and proposed conclusion before a final PASS is issued.

The co-reviewer must document:

- identity and role;
- independence/conflict declaration;
- material evidence reviewed;
- scope and coverage identifiers;
- conclusion;
- signature or authenticated approval;
- date/time.

The customer must not control the selection or compensation of the independent co-reviewer.

## 12. Sampling and Methodology Oversight

The provider must maintain a pre-declared retrospective sampling mechanism for Enterprise Pilot audits sufficient to test whether assessments are being performed consistently with the methodology.

The sampling population, inclusion rules, freeze point, minimum sample floor, selection mechanism, and reviewer independence requirements must be declared before the sampled population can be manipulated in response to results.

Sampling does not certify every audit. It is an oversight control and evidence about methodology execution.

Where an external or independently verifiable selection mechanism is used, its seed/selection record must be preserved with the audit history.

## 13. Stopping Criteria

Stopping criteria must be established before substantive path enumeration begins.

Resource, time, or access constraints may result in PARTIAL or UNVERIFIED results. They may not silently convert incomplete coverage into PASS.

The assessor must record the point at which enumeration stopped and the unresolved coverage resulting from that decision.

## 14. Historical Integrity

The provider must preserve the original Scope Declaration, Coverage Declaration, evidence identifiers, methodology version, findings, result, validity state, and signatures.

Historical records must not be overwritten to create a cleaner retrospective narrative.

A superseding Audit is a new record. It does not erase the existence or result of an earlier Audit.

## 15. Public Representation

Any provider-issued public representation of PASS must preserve, at minimum:

- Audit identifier;
- report/version identifier;
- validity/review date;
- scope identifier;
- coverage identifier;
- bounded nature of the conclusion.

Where a superseding Audit follows a prior non-PASS result for the same materially relevant boundary, the public representation must not imply that the prior result never existed.

The specification cannot directly control third-party statements. Customer agreements should therefore require accurate attribution and reference to the authoritative Audit record when the customer publicly represents an Audit result.

## 16. Track Record

Methodology validation history must distinguish:

- internal testing;
- external pilot engagements;
- independent replication;
- production experience.

The provider must disclose the number and nature of external engagements supporting any claim about real-world validation.

A small number of favorable engagements must not be represented as a population-level reliability rate.

The provider must disclose material selection effects when its customer population is not representative of the systems for which the methodology is being discussed.

## 17. Disputes and Reassessment

Material disputes about scope membership, coverage, classification, methodology, or validity enter documented review.

If unresolved by the engagement's defined deadline, the affected result becomes:

> **UNVERIFIED — CLASSIFICATION DISPUTE**

A dispute mechanism is not a substitute for independent co-review.

Material newly discovered evidence may trigger reassessment even when the original customer has not raised a dispute.

## 18. Human Stop Cut Limitation

A Human Stop Cut is a property of a declared transition system and its enforcement assumptions. It is not a general theorem about arbitrary programs, agents, tools, or the external world.

For open-world systems, reachability may be undecidable or materially incomplete. DAR therefore treats model completeness, boundary fidelity, observability, and enforcement assumptions as explicit evidence targets and limitations.

## 19. Non-Claims

DAR Boundary Audit is not:

- a safety certification;
- a security certification;
- a legal opinion;
- a regulatory approval;
- a guarantee of future system behavior;
- proof that unknown paths do not exist;
- proof that an arbitrary AI cannot produce a prohibited outcome.

## 20. Accountable Assessor

The primary assessor and independent co-reviewer are named in every final Audit.

Signing means that the signer personally reviewed the final report and the evidence necessary to support the stated conclusion immediately before approval.

Automated or unattended signatures are insufficient.

## 21. Liability and Contractual Boundary

The commercial engagement must define scope, permitted reliance, customer responsibilities, evidence obligations, change notification, confidentiality, dispute handling, limitations of liability, and insurance requirements as appropriate to the engagement.

The specification is not a substitute for legal advice or a negotiated contract. Commercial deployment should be reviewed by qualified counsel in the relevant jurisdiction.

## 22. Design Principle

> **Do not claim authority that the evidence does not establish.**

The same principle applies to the Audit itself:

> **Do not claim an assurance level that the audit process does not establish.**

## 23. Release Gate

This Enterprise Pilot specification is intended for controlled first-customer use, not as a universal certification standard.

Before each engagement, the provider must verify that:

- the current specification version is identified;
- scope and coverage are frozen;
- the reference baseline is mapped;
- pre-scope provenance is recorded;
- the primary assessor and independent co-reviewer are named;
- conflicts are disclosed;
- evidence and configuration identities are recorded;
- stopping criteria are fixed;
- result semantics are understood;
- limitations and validity are stated;
- reassessment triggers are documented.

The pilot exists to generate real external evidence about the methodology while preserving bounded claims and explicit accountability.
