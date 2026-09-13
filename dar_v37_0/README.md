# DAR-MA v1

DAR-MA extends Decision Accountability Review from single effects to distributed multi-agent outcomes.

## Core invariant

> After a named human authority issues `NO`, no authorized execution path within the declared Outcome Boundary may produce the prohibited outcome.

## Reference concepts

- **Outcome Contract** — names the protected outcome, scope, and human authority.
- **Stop Epoch** — makes refusal persistent in the reference model and invalidates prior delegated authority.
- **Delegation Monotonicity** — child authority cannot exceed parent authority.
- **Outcome Dependency Graph** — models distributed execution paths that can compose into an outcome.
- **Human Stop Cut** — every enumerated path to a protected outcome must cross an enforcement point.

## Attack classes

A-13 through A-18 cover multi-agent composition, delegation widening, stop-epoch replay, alternate paths, outcome substitution, and graph drift.

## Scope

This is a reference model and research specification. It does not prove control over arbitrary emergent behavior, hidden interfaces, compromised infrastructure, or world-level outcomes.

See `DAR_MA_SPEC_v1.md` and `test_multi_agent.py`.
