# DAR-MA v1 — Multi-Agent Outcome Boundary

## Status

Research specification and reference model. DAR-MA extends DAR from a single-effect boundary toward distributed, multi-agent outcomes. It is not a production security certification.

## Core property

For a declared significant outcome `O`, if the named human authority issues `NO`, then no authorized execution path within the declared Outcome Boundary may produce `O`.

The claim is bounded by what the system can define, observe, attribute, and enforce.

## 1. Outcome Contract

Every protected outcome MUST have an Outcome Contract:

- `outcome_id`
- `scope`
- `authority`
- stop semantics
- declared enforcement boundary

An outcome is preferable to an API as the protected object when multiple agents or interfaces can compose the same consequential result.

## 2. Stop Epoch

A refusal creates a monotonically increasing Stop Epoch for the protected outcome. Capabilities and delegations issued under an invalidated epoch MUST NOT remain usable after the stop.

The v1 reference model uses persistent stop semantics: resumption requires a distinct positive authorization mechanism, which is intentionally not part of the reference model.

## 3. Delegation monotonicity

Delegation MUST NOT widen the outcome authority of the delegating principal:

`Authority(child) ⊆ Authority(parent)`

A child cannot obtain an outcome that its parent did not already possess.

## 4. Outcome Dependency Graph

A protected outcome is represented as a directed execution/dependency graph. A Human Stop Cut is a set of enforcement edges such that every enumerated source-to-outcome path crosses an enforcement point.

For the finite reference graph:

`∀ p ∈ Paths(System,O): p ∩ StopCut ≠ ∅`

Graph coverage is evidence about the declared graph, not proof that the real-world system contains no unmodeled path.

## 5. Multi-agent composition

The framework explicitly tests the case where individually permitted actions compose into a prohibited outcome:

`A(X) ∧ B(Y) ∧ (X + Y → O)`

Local authorization is therefore insufficient evidence when the consequential property is emergent.

## 6. Observability boundary

DAR-MA distinguishes three outcome classes:

1. explicit effect outcomes;
2. state-based outcomes;
3. emergent/world-level outcomes.

The higher the semantic distance between an authorized action and the protected outcome, the stronger the need for explicit instrumentation and assumptions. DAR-MA MUST NOT silently promote an unobservable outcome into a proven security property.

## 7. Registered attacks

DAR-MA v1 introduces the following multi-agent attack classes:

- **A-13 Multi-Agent Composition Bypass:** individually authorized agents compose a prohibited outcome.
- **A-14 Delegation Widening:** a child receives broader outcome authority than its parent.
- **A-15 Stop-Epoch Replay:** an old delegation/capability remains usable after refusal.
- **A-16 Alternate-Path Outcome:** an unmodeled interface reaches the protected outcome without crossing the Human Stop Cut.
- **A-17 Outcome Substitution:** authorization for one outcome is transformed into another through delegation or composition.
- **A-18 Graph Drift:** the declared dependency graph no longer matches the deployed execution graph.

## 8. Evidence levels

- **Model evidence:** the reference model satisfies its unit tests.
- **Differential evidence:** a separately written implementation reproduces the public profile. If written by the same research effort, it MUST be called self-authored differential reproduction.
- **Deployment evidence:** the declared multi-agent boundary is tested in the target environment.
- **Independent replication:** an unrelated team reproduces the result from the public specification. This is the strongest external validation target and remains open until performed.

## 9. Explicit non-claims

DAR-MA does not prove that an arbitrary advanced AI cannot generate a prohibited outcome. It does not solve unrestricted emergent behavior, compromised infrastructure, hidden interfaces, or world-level causal control. It provides a framework for making a narrower outcome-boundary claim precise enough to test.
