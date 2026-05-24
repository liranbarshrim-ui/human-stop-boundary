# DAR Layer II — Internal Memo
## Adversarial Review: Where Does the Taxonomy Fail?

*Working document — May 2026*
*Classification: Internal only. Not for distribution.*
*Status: Freeze v0.2 — adversarial testing phase*

---

## Explicit Boundary Statement

Layer II performs best where refusal authority can be bounded to a discernible actor, role, or protocol. Distributed authority systems — ICU triage under overload, multi-regulator coordination, board crises with contested legitimacy — remain partially legible but resist clean classification.

This is not a flaw to be fixed. It is a boundary to be stated.

---

## What We Have

Layer II proposes a taxonomy of where refusal authority lives:

**PERSON** — authority exists only in an individual. Disappears with them.
**ROLE** — authority is attached to the title. Survives if the role is documented and bounded.
**STRUCTURE (Held)** — authority is encoded in governance artifacts and has demonstrably survived pressure. Survives automatically, without succession decisions.
**STRUCTURE (Declared)** — authority is written down but untested under pressure. May hold; may not. Indistinguishable from ROLE without a stress event.
**UNLOCATED** — no identifiable anchor. Authority cannot be recovered.
**UNKNOWN** — insufficient public evidence to classify.

The central question: *Is the name portable?*

The taxonomy has been tested against eight cases across five domains. In each case, it produced a classification that adds explanatory power beyond Layer I. It distinguishes between Toyota (STRUCTURE) and Knight Capital (UNLOCATED) in a way that "authority exists" or "authority failed" cannot.

Two secondary observations have also emerged:

**Authority Survivability:** Does refusal authority survive the absence of the person who held it?

**External Authority Substitution:** When internal authority fails, can an organization access external authority? (Southwest → FAA)

---

## Counterarguments — Attempted Breaks

### Break Attempt 1: The taxonomy conflates description with prescription

*The objection:* PERSON / ROLE / STRUCTURE describes where authority happens to sit, not where it should sit. This makes it descriptive, not normative. A purely descriptive taxonomy has limited governance value — it tells you what you observe, not what to do.

*Evaluation:* Partially valid. The taxonomy is, by design, observational. But the DAR framework is not neutral: it asserts that STRUCTURE is preferable to PERSON, because STRUCTURE survives absence. This is a normative claim embedded in the observation. The taxonomy does not pretend otherwise. The prescription is implicit: organizations should move toward STRUCTURE on the axis that matters to DAR — refusal authority over irreversible decisions.

*Verdict: Partial hit. The memo should be explicit that the taxonomy is observational but not value-neutral.*

---

### ROLE as unstable middle — a feature, not a bug

ROLE is not a stable endpoint. It is a transitional classification on a gradient:

PERSON → ROLE → STRUCTURE

But ROLE is always vulnerable to regression: ROLE → PERSON under pressure, informal hierarchy, or organizational change. JPMorgan pre-2012 was formally ROLE. Under pressure it operated as PERSON. Boeing was formally ROLE. It degraded to fragmented PERSON over years.

This means: ROLE should be presented with its trajectory, not just its label. A ROLE classification that is stable over time and has survived pressure is moving toward STRUCTURE. One that degrades under load is moving toward PERSON.

*ROLE is the unstable middle.*



*The objection:* ROLE assumes that titles carry authority reliably. But titles are reinterpreted constantly — under pressure, organizational change, or simple ambiguity. The difference between ROLE and PERSON is thinner than claimed. An FDA Division Director is a role, but if no one challenges a rogue holder of that role, does ROLE actually hold? JPMorgan's CIO risk committee was technically a ROLE structure, and it still failed.

*Evaluation:* This is the strongest counterargument. ROLE is conditionally stable. It depends on: (a) the authority being explicitly written into the role, not just assumed; (b) the organizational culture enforcing what the role says; (c) the absence of informal networks that override formal roles. JPMorgan pre-2012 shows ROLE degrading to PERSON under pressure. This is not a flaw in the taxonomy — it reveals a gradient. But the memo should acknowledge that ROLE is not a stable endpoint, only a midpoint.

*Verdict: Valid partial break. ROLE should be presented as a transitional classification, not a stable one. The trajectory column matters more than the static label.*

---

### Break Attempt 3: STRUCTURE is also vulnerable — it can be nominal

*The objection:* STRUCTURE can be written down without being real. A governance charter can specify that "the CRO has independent authority to halt any transaction above X threshold" — and that authority can still be ignored in practice because of culture, hierarchy, or the CEO's informal power. The written structure exists; the actual authority does not. FAA protocols are documented, but ATC has had failures where the documented structure was not followed.

*Evaluation:* Valid, and important. STRUCTURE (documented) is not identical to STRUCTURE (operative). The taxonomy currently conflates them. This is a genuine limitation. A refinement would distinguish between Documented Structure and Operative Structure. The observable test: when pressure mounted, did the structure hold without a succession decision? If yes, operative. If no, nominal. This may be testable in some cases but not all from public record.

*Verdict: Genuine weakness. The taxonomy needs a note that STRUCTURE describes documented intent, not necessarily operative reality. This does not break the taxonomy — it qualifies it.*

---

### Break Attempt 4: External Authority Substitution is not a new axis — it is an edge case

*The objection:* The Southwest → FAA pattern is interesting but not generalizable. Most organizations cannot "borrow" external interruption authority. Southwest could only do this because FAA has formal jurisdiction over flight operations. This is a regulatory artifact, not a governance insight. Making it an axis of the taxonomy adds complexity without explanatory power for non-regulated industries.

*Evaluation:* Partially valid. The substitution pattern is domain-specific: it requires that an external authority with STRUCTURE exists and is accessible. In financial markets, this is occasionally the exchange (circuit breakers). In clinical trials, this is the FDA. In other domains, no such authority exists — which may itself be significant. Rather than a separate axis, External Substitution might be better captured as a sub-classification: UNLOCATED (with external fallback) versus UNLOCATED (without external fallback). Knight Capital falls in the latter. Southwest falls in the former.

*Verdict: Valid refinement. External Substitution is a modifier, not a new axis. The taxonomy is cleaner without it as a standalone dimension.*

---

### Break Attempt 5: Hospital ICU triage — can the taxonomy classify distributed, dynamic, ethically constrained authority?

*This is the designed failure test.*

During COVID-19 peak periods, ICU triage authority was:
- Distributed across attending physicians, charge nurses, ethics committees, and in some jurisdictions, state-level triage protocols
- Dynamic: changed as capacity changed
- Ethically constrained: refusal to admit was not purely operational, it was clinical and moral
- Partly documented: some hospitals had published triage protocols; others did not; some had ethics committee override; some did not

*Layer I question:* Who could refuse a patient admission?
*Layer II question:* Did that refusal authority survive the shift change of the physician who held it?

*Preliminary classification attempt:*

Hospitals with published triage protocols and ethics committee review: ROLE → STRUCTURE (partial). The role of attending physician or ethics committee chair is defined, but the protocol survivability depends on whether the protocol was actually binding or advisory.

Hospitals without published protocols: PERSON. The attending on shift made the call. The next attending might make a different call. No documented continuity mechanism.

*Does the taxonomy break?*

Not entirely. The ICU case reveals a challenge the taxonomy handles imperfectly: multi-actor authority where no single person or role holds clear refusal authority. In surgical timeout, any team member can halt — STRUCTURE. In ICU triage, the authority is distributed across clinical, ethical, and administrative layers in ways that do not fit neatly into a single classification.

*Verdict: Genuine stress fracture. The taxonomy works cleanly for single-point authority (one person, one role, one protocol). It struggles with distributed multi-actor authority under overload conditions. This is a real limitation, not a fatal flaw. The taxonomy should acknowledge that distributed authority systems may require a composite classification.*

---

## Summary of Adversarial Findings

| Counterargument | Verdict | Action |
|---|---|---|
| Descriptive, not prescriptive | Partial hit | Make normative stance explicit |
| ROLE is unstable | Valid partial break | Present ROLE as transitional, not stable |
| STRUCTURE can be nominal | Genuine weakness | Add: documented vs. operative distinction |
| External Substitution is an edge case | Valid refinement | Reclassify as modifier, not axis |
| ICU distributed authority | Genuine stress fracture | Acknowledge composite authority limitation |

---

## What Layer II Can Claim After Adversarial Testing

**Scope condition:** Layer II is strongest where refusal authority is expected to be nameable, bounded, or formally delegated. It weakens in distributed adaptive systems where authority is inherently collective, dynamic, or contested.

**It can claim:** Consistent explanatory power across heterogeneous governance environments. The taxonomy distinguishes between observable patterns of authority location in a way that Layer I cannot.

**It cannot claim:** That STRUCTURE is always operative, that ROLE is stable, or that the taxonomy cleanly handles distributed multi-actor authority systems.

**The central observation remains intact:** Role continuity is asserted. Authority continuity was never separated from the person who held it. The taxonomy is the instrument for making that observation precise.

---

---

## Hard Case: Silicon Valley Bank, 2021–Q1 2023

*Forensic test — pre-collapse governance only*

**Five questions:**

**Layer I — Who was authorized to refuse continuation of balance-sheet risk exposure?**
CRO Laura Izurieta until April 2022. After her departure: no named authority. The Fed found explicitly: "It is unclear how the bank managed risks in the interim." Risk senior leadership "held the responsibilities" — but no documented delegation, no interim authority named.

**Layer II — Where did that authority live?**

Before April 2022: ROLE. CRO with documented reporting line to Board Risk Committee.

April 2022 – January 2023: UNLOCATED. The role went vacant. No person held it. No documented delegation transferred it. The Fed's language is the evidence: unclear.

**Board Risk Committee — STRUCTURE (Declared) or STRUCTURE (Held)?**
The committee existed and doubled its meetings from 7 to 18 in 2022 — evidence of awareness. But the Fed found the board "did not receive adequate information from management about risks" and "did not hold management accountable." STRUCTURE (Declared). Insufficient evidence for Held. The structure existed in documentation; refusal survivability is not evidenced under pressure.

**Growth override — modifier hypothesis, not causal inference:**
Executive growth priorities coincided with authority discontinuity. SVB changed its own risk-management assumptions to reduce how risks were measured rather than addressing the underlying risks. Possible modifier: growth priority may have contributed to authority continuity failure. This remains hypothesis, not established inference.

**Irreversibility threshold:**
Interest rate hedges removed 2021–2022. Supervisory finding issued November 2022. Bank collapsed before rating downgrade was finalized. Continuation became effectively irreversible during the CRO gap period — when refusal authority was UNLOCATED.

---

**Classification: ROLE → UNLOCATED**

This is a distinct pattern not previously observed:

Boeing / JPMorgan pre-2012: ROLE → PERSON. Authority was absorbed by informal hierarchy or dominant individuals.

SVB: ROLE → UNLOCATED. Authority did not migrate to a person. It collapsed into absence.

Knight Capital: UNLOCATED (native). Never anchored.

SVB is the first case of anchored → degraded → unlocated. The anchor existed. It was removed. Nothing replaced it.

**New formulation:** Not all authority degradation ends in a person. Some degradation ends in absence.



*Forensic test — no retrospective overfitting*

**Five questions:**

**What was documented?** The nonprofit board had legal authority to fire the CEO. Charter explicit: mission over profit, no investor board seats. STRUCTURE (Declared).

**Who held formal authority?** Four of six board members. Legally binding vote. They fired Altman.

**Who held operative authority?** 700 of 770 employees threatening to resign. Microsoft offering to hire them all. Investors applying pressure behind the scenes. Altman running a counter-movement within hours.

**Did authority survive pressure?** No. Within 96 hours, the board that held formal authority collapsed. Not through legal challenge but through organizational gravity.

**Classification:** STRUCTURE (Declared) that failed to hold. Formal authority existed. Operative survivability did not.

---

**The temptation here is to add NETWORK as a fifth category.**

The authority that prevailed was distributed across an informal network — employees, investors, Microsoft — with no single named actor and no documented authority. This looks like something the taxonomy cannot classify.

**The correct restraint:** NETWORK is a mechanism of override, not a location of authority. Layer II asks where refusal authority lives, not what can overpower it. The board held the authority. The network overrode it. These are different axes.

If NETWORK enters as a category, it begins consuming PERSON and ROLE — because informal network power is present in nearly every case: JPMorgan pre-2012 had Jamie Dimon gravity, Boeing had political and commercial network pressure, Southwest had frontline crew networks improvising. Adding NETWORK as a class would reduce the taxonomy's precision.

**Working conclusion:** OpenAI 2023 = STRUCTURE (Declared) with Network Override modifier.

Network Override is a modifier hypothesis, not a class. It requires 2–3 additional cases with the same pattern before elevation to category status. Candidates: Uber/Travis Kalanick board, WeWork/Neumann, Disney/Iger succession, SVB risk governance pre-collapse.

**The taxonomy held. Its boundary became clearer.**



## Observable Authority Degradation Patterns — v0.2

STRUCTURE (Held): Toyota, FAA ATCSCC. Stable by design.
ROLE → STRUCTURE: JPMorgan post-2013. Institutionalizing after failure.
ROLE → PERSON (passive drift): Boeing, JPMorgan pre-2012. Authority absorbed by individuals under cultural or growth pressure.
ROLE → PERSON (removal override): Lehman 2007. Refusal authority formally assigned, exercised, then role holder removed after documented friction with executive direction. Operative authority concentrated in CEO.
ROLE → UNLOCATED: SVB 2022. Authority collapsed into absence.
UNLOCATED (native): Knight Capital. Never anchored.

**Modifiers note:** Mechanisms of degradation are observational modifiers, not additional taxonomy classes. Passive drift, removal override, and vacuum are all sub-patterns of ROLE → PERSON or ROLE → UNLOCATED. They describe how degradation occurred, not a distinct location of authority.

**Lehman boundary:** Antoncic raised risk concerns at odds with executive direction and was subsequently removed from the role. Causality between refusal and removal is documented in alignment but not established as direct cause.

1. ICU triage — classified: ROLE approaching STRUCTURE (Declared) where protocols exist. PERSON where protocols absent. Variance by institution.
2. The documented vs. operative STRUCTURE distinction resolved by Held/Declared refinement.
3. ROLE confirmed as transitional marker, not endpoint.
4. Negative case pending — Microsoft/Nadella 2014. Hypothesis: Layer II adds little explanatory power where continuity held without visible refusal discontinuity. If silent — that is information, not failure.

**Do not update the website until negative case is complete.**

The taxonomy has passed v0.2 stress testing with qualifications. It is not broken. It is bounded.

---

*DAR Internal — Working model v0.2*
*Decision Authority Research / matrix-audit.com*
*Not for external distribution*
