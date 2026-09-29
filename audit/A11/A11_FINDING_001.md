# A11-F001 — Protected / Non-Protected Effect Surface Separation

**Status:** NOT PROVEN  
**Category:** A11 Boundary Completeness  
**Scope:** Deployment-level protected outcome boundary

## Finding

The current implementation contains distinct protected and ordinary execution paths. The available code evidence does not, by itself, establish that the ordinary effect surface is disjoint from the authoritative target of the protected outcome.

The relevant property is:

`ordinary effect surface ∩ protected outcome surface = ∅`

This has not yet been established at deployment level.

## Attack Question

> Given a valid refusal for protected outcome X, identify every process, IPC endpoint, adapter, filesystem target, database connection, child process, helper, integration, or alternate execution path capable of producing X without traversing protected_commit(X).

If any such path can produce X:

**A11 = FAIL**

If deployment evidence establishes that no such path exists:

**A11 = PASS**

If the evidence is insufficient:

**A11 = NOT PROVEN**

## Current Execution Graph

### Ordinary

```
CLIENT
  |
  v
UnixDispatcherServer
  |
  v
EffectRequest
  |
  v
EffectGate.execute()
  |
  v
PrivilegedDispatcher._apply()
  |
  v
READ / WRITE
  |
  v
root-relative filesystem target
```

### Protected

```
Protected Request
  |
  v
EffectGate.execute_protected()
  |
  v
EffectTxn
  |
  v
protected_commit()
  |
  v
FencedEffectAdapter
  |
  v
External authoritative system
  |
  v
PROTECTED OUTCOME X
```

## Critical Question

The ordinary filesystem path is not automatically a bypass.

It becomes an A11 failure only if the deployment allows that ordinary path to produce the same externally observable protected outcome X.

Therefore the required question is:

> **Can the ordinary effect surface produce the same authoritative outcome that the protected surface claims to fence?**

## Outcome Identity Limitation

DAR validates the syntactic form of `outcome_key`; it does not infer business-semantic equivalence.

Therefore:

`X = outcome_key A`

and:

`Y = outcome_key B`

does not establish that X and Y are different real-world outcomes.

The deployment/business protocol must establish the mapping.

A semantic alias where Y produces the same real-world outcome as refused X is an A11 failure.

If that equivalence cannot be established from deployment evidence, the branch remains NOT PROVEN.

## Required Deployment Evidence

The external reviewer should identify every:

- process
- UID / principal
- IPC endpoint
- socket / pipe / queue
- adapter
- filesystem target
- database connection
- external API
- child process
- helper
- plugin
- recovery path
- startup path
- administrative interface

that could potentially produce X.

The reviewer should then establish whether each surface:

1. reaches X;
2. requires the protected fence;
3. can bypass the fence;
4. is semantically equivalent to another representation of X.

## Required Deliverable

Produce a deployment target matrix covering every reachable effect surface:

| Component | Process / UID | Interface | Target | Effect | Protected? | Fence Required? | Can Produce X? | Evidence | Status |
|---|---|---|---|---|---|---|---|---|---|
| Protected adapter | — | commit | authoritative target | X | YES | YES | TBD | deployment evidence | TBD |
| Ordinary dispatcher | — | UNIX socket | filesystem root | WRITE | NO | NO | TBD | deployment evidence | TBD |
| Database connection | — | DB | TBD | mutation | TBD | TBD | TBD | deployment evidence | TBD |
| Helper process | — | IPC/subprocess | TBD | TBD | TBD | TBD | TBD | deployment evidence | TBD |

## Resolution Criteria

This finding can be closed only when deployment evidence establishes:

`ordinary effect surface ∩ protected outcome surface = ∅`

or when a discovered overlap is explicitly addressed and the resulting deployment is re-audited.

Until then:

**A11-F001 remains NOT PROVEN.**

## Important Distinction

This finding is not a claim that DAR is vulnerable.

It is a statement that the relevant deployment-level separation property has not yet been demonstrated.

That distinction is intentional and is part of the A11 methodology.
