# DAR — Core Doctrine

**Decision Accountability Review (DAR)**

Defined by Liran Bar-Shrim.

## 1. The problem

A system can have people who are responsible on paper while lacking anyone whose refusal is structurally binding.

DAR begins from a narrower question:

> **When a decision or effect must stop, whose refusal is authoritative, and what prevents the process from continuing around it?**

The objective is not to make a system incapable of acting. It is to make the boundary between authorization and execution explicit, attributable, testable, and resistant to unauthorized continuation.

## 2. Foundational qualification

A claimed stop authority is meaningful only if its authority is qualified before the process reaches the point at which it is supposed to exercise that authority.

Qualification therefore asks whether the authority is:

- explicitly identified;
- bound to a defined scope;
- recognized by the process that executes the effect;
- protected from being silently widened by the actor it constrains; and
- independently testable as a condition of continuation.

## 3. Axiom 1 — Authority Self-Containment

> **No authority may define, evaluate, modify, or override the conditions of its own authority.**

The authority that is subject to a boundary must not be the sole authority that determines whether that boundary exists, what it means, or whether it applies.

This is a structural constraint, not a statement about the intentions of an actor.

## 4. Axiom 2 — No Sovereignty by Origin

An actor does not acquire sovereign authority merely because it originated, created, owns, operates, or controls the mechanism through which an authority was initially established.

Origin is not qualification.

A system therefore cannot derive unrestricted authority from the fact that it generated the policy, process, model, software, or delegation under which it later acts.

## 5. Freeze Principle

Once a boundary condition has been qualified as binding, the actor operating inside that boundary cannot unilaterally relax, redefine, or bypass the condition in order to continue the same authority.

A change to authority is itself an authority-sensitive event.

## 6. Structural Irrevocability

A stop condition is stronger than an instruction that an actor may choose to obey.

For the controlled effect universe, the desired property is structural:

> **When the qualified stop condition is active, the controlled process cannot legitimately continue through an alternate path that bypasses the boundary.**

This is deliberately scoped. DAR cannot make an external system obey a boundary that is not actually connected to its effects.

## 7. Non-Redundancy

The principles are intentionally distinct:

| Principle | Function |
|---|---|
| Foundational Qualification | establishes that a claimed authority has the required standing and scope |
| Authority Self-Containment | prevents authority from defining or modifying its own governing conditions |
| No Sovereignty by Origin | prevents origin, authorship, ownership, or creation from becoming sovereign authority by itself |
| Freeze Principle | prevents unilateral relaxation of an already-qualified boundary during the governed process |
| Structural Irrevocability | defines the required operational property: a valid stop must bind continuation inside the controlled effect universe |

Removing one of these can reopen a different failure mode; they are not merely repetitions of the same rule.

## 8. The engineering translation

The software prototype translates these ideas into a bounded enforcement mechanism:

1. **Named authority** — capabilities are bound to a principal and domain.
2. **Typed effect** — the action/effect class is explicit rather than inferred from arbitrary code.
3. **Generation binding** — capabilities are bound to the current state and process generation.
4. **Attenuation** — the prototype rejects permission expansion and unauthorized governance mutation.
5. **Durable consumption** — replay and effect state are persisted before the external effect proceeds.
6. **Recoverable intent** — an external effect has a durable idempotency identity and parameter digest.
7. **Fail-closed preparation** — a recoverable effect is not externally executed unless its PREPARED record can be durably established.
8. **Authoritative commit** — successful return from an adapter is not by itself treated as proof of external commitment.
9. **Reconciliation** — post-crash pending state can be reconciled against authoritative adapter status and validated journal state.
10. **Rollback boundary** — authenticated state is not sufficient against restoration of an older valid snapshot; rollback protection requires a trusted monotonic anchor outside the Store rollback domain.

## 9. What DAR does not claim

DAR does **not** claim that it can universally stop an arbitrary AI system, model, autonomous agent, government, organization, or attacker.

Its security claims are bounded by the actual enforcement boundary. If an effect is outside that boundary, DAR has no structural authority over it.

DAR also does not claim:

- anti-rollback without an external trust anchor;
- exactly-once semantics for arbitrary external side effects without an authoritative idempotent adapter;
- protection against an attacker who already controls the trusted enforcement root;
- production certification or independent security audit.

## 10. Evidence discipline

A DAR claim is only as strong as the evidence chain supporting it.

The required chain is:

**artifact → fresh repository checkout → exact source comparison → execution → observed result → bounded claim**

Chat-pasted files, snippets, screenshots, generated summaries, and remembered versions are **unverified artifacts** until compared with the repository state actually executed.

This distinction is operationally important: a test result produced from one version must never be presented as evidence for another version merely because their filenames or descriptions are similar.

## 11. Operational test

The simplest DAR question is also the most important:

> **If the designated authority says “stop,” can the controlled process continue anyway?**

The answer must be established structurally for the specific process and effect universe being claimed—not assumed from policy language, organizational charts, or model behavior.

## 12. Status of the v36.14 prototype

v36.14 is a hardened research prototype and an auditable candidate implementation. It is evidence for the bounded properties actually exercised by its tests and runtime boundary checks. It is not evidence of universal AI control or a substitute for deployment-specific security engineering and independent review.
