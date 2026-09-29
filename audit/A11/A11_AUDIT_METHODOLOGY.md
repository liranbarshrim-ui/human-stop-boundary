# A11 AUDIT METHODOLOGY

## Adversarial Boundary Completeness for Protected Outcomes

**Status:** Audit Methodology  
**Version:** 1.0  
**Scope:** Deployment-level adversarial review of a protected effect boundary

## 1. Purpose

A11 is an adversarial audit of boundary completeness.

It does not ask whether DAR is secure. It asks:

> Given a protected outcome X, does the deployment contain any ordinary or alternate execution surface capable of producing X without traversing the authoritative protected commit path?

The object of the audit is the deployed system and its effect surface, not the DAR code in isolation.

## 2. Core A11 Question

> Given a valid refusal for protected outcome X, identify every process, IPC endpoint, adapter, filesystem target, database connection, child process, helper, integration, or alternate execution path capable of producing X without traversing protected_commit(X).

If such a path exists: **A11 = FAIL**.

If deployment evidence establishes that the protected and ordinary surfaces cannot produce the same outcome: **A11 = PASS**.

If evidence is insufficient to establish either condition: **A11 = NOT PROVEN**.

## 3. 10K vs A11

**10K qualification** tests resilience within the declared fenced surface: replay resistance, crash recovery, concurrency, refusal persistence, fence races, idempotency, restart persistence, and reconciliation.

**A11** tests whether the same protected outcome can be produced somewhere else.

A system can pass extensive 10K testing and still fail A11 if an alternate execution surface can produce the protected outcome without passing through the fence.

## 4. Protected Outcome Definition

A11 begins with the definition of the protected outcome. X must be defined by the deployment/business protocol, not inferred from DAR identifiers.

The auditor must determine:

1. What exactly constitutes X?
2. Which system is authoritative for X?
3. Which resource changes when X occurs?
4. Which process performs that change?
5. Which interface permits that change?
6. Is the effect reversible or irreversible?
7. What evidence proves X actually occurred?

A DAR journal entry alone does not establish the real-world outcome.

## 5. Effect Identity vs Outcome Identity

`effect_id` identifies a protocol invocation.

`outcome_key` identifies the protected outcome within the deployment protocol.

DAR does not infer semantic equivalence between outcomes merely because identifiers or parameters appear related.

A11 therefore includes a **Semantic Alias Attack**:

REFUSE(X) -> alternate request -> Y -> Y produces the same real-world outcome as X.

If yes: **FAIL**.  
If the deployment cannot establish the equivalence relation: **NOT PROVEN**.

## 6. Primary Deployment Graph

```
                    PROTECTED OUTCOME X
                           |
                  definition supplied
                   by deployment
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
   FENCED SURFACE                    ORDINARY SURFACE
          |                                 |
 execute_protected()                 execute()
          |                                 |
 protected_commit()                    _apply()
          |                                 |
 FencedEffectAdapter                  filesystem
          |                                 |
          v                                 v
 External target?                     root/path
          |                                 |
          +----------------+----------------+
                           |
                           v
                    SAME TARGET?
                       /       \
                     YES       NO
                      |         |
                    FAIL     candidate
                              PASS
```

NO is not sufficient by itself. The auditor must establish that no alternate mechanism elsewhere in the deployment can reach X.

## 7. Ordinary Surface

For every ordinary execution surface, document:

- process
- UID / principal
- executable
- IPC endpoint
- socket / pipe / queue
- callable interface
- adapter
- filesystem root
- database connection
- network connection
- child processes
- helper processes
- plugins
- environment-controlled behavior
- recovery paths
- startup paths
- administrative paths

Current known ordinary path:

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

The relevant question is not whether this path is restricted, but whether it can produce X.

## 8. Protected Surface

Current protected path:

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

The auditor must establish which component is authoritative for the actual outcome.

## 9. Surface Intersection

The central A11 test is:

`ORDINARY EFFECT SURFACE ∩ PROTECTED OUTCOME SURFACE`

If the ordinary surface can produce X while refusal(X) is authoritative: **FAIL**.

If deployment evidence establishes that the ordinary surface cannot produce X: **PASS**.

If neither can be established: **NOT PROVEN**.

## 10. Attack Classes

### A11-A — Alternate Effect Path
Can an ordinary API, helper, process, or integration produce X without protected_commit(X)?

### A11-B — Direct Adapter Invocation
Can an adapter or external authority be invoked directly without passing through the protected gate?

### A11-C — Alternate IPC
Can another socket, pipe, queue, RPC endpoint, HTTP endpoint, or local IPC mechanism produce X?

### A11-D — Filesystem Overlap
Can the ordinary filesystem surface modify the same authoritative resource representing X?

### A11-E — Database Bypass
Can another database connection, credential, query path, migration, helper, or administrative interface produce X without the fence?

### A11-F — Child / Helper Delegation
Can an authorized process delegate the effect to a child process or helper that bypasses the protected path?

### A11-G — Recovery / Reconciliation Bypass
Can startup, crash recovery, reconciliation, or pending-intent processing produce X without satisfying the protected refusal/fence?

### A11-H — Deprecated or Legacy Interface
Does an old API, compatibility path, administrative interface, or legacy deployment path still permit X?

### A11-I — Capability Forgery
Can an attacker construct a capability whose effect differs from the requested effect? Cryptographic binding and request validation should be checked explicitly.

### A11-J — Semantic Alias
Can an attacker refuse X and commit Y where Y is the same real-world outcome? If yes: FAIL. If equivalence is not established: NOT PROVEN.

## 11. Refusal-Based Test

1. Define protected outcome X.
2. Establish a valid refusal for X.
3. Attempt X through protected_commit(X).
4. Attempt X through every discovered ordinary/alternate surface.
5. Attempt semantically equivalent representations of X.
6. Observe the authoritative external system.
7. Determine whether X occurred.

The decisive observation is the authoritative outcome, not merely the DAR response.

## 12. Evidence Requirements

Relevant deployment evidence includes:

- process list
- process ownership
- UID/GID configuration
- socket inventory
- IPC inventory
- filesystem permissions
- filesystem targets
- mount configuration
- database connections
- credentials and roles
- adapter implementations
- external API endpoints
- child-process relationships
- service configuration
- startup configuration
- recovery configuration
- network listeners
- deployment manifests
- container configuration
- system service definitions
- authoritative transaction records
- refusal/fence state
- observed external effect

Source-code inspection alone is insufficient where the claim concerns deployment separation.

## 13. Finding Classification

### PASS
Sufficient evidence establishes that the protected outcome is explicitly defined, the authoritative target is identified, relevant reachable surfaces have been examined, and no ordinary/alternate path can produce X without the required fence.

### FAIL
A concrete alternate path exists that can produce the protected outcome without traversing the required protected commit/fence.

### NOT PROVEN
The reviewer cannot establish either separation or overlap.

This is not equivalent to PASS and is not equivalent to FAIL.

## 14. Current Finding

### A11-F001 — Protected / Non-Protected Effect Surface Separation

**Status: NOT PROVEN**

The implementation demonstrates distinct protected and ordinary execution paths. However, currently available deployment evidence does not establish that the ordinary effect surface is disjoint from the authoritative target of the protected outcome.

Therefore:

`ordinary root ∩ protected target = NOT PROVEN`

Required evidence: the deployment must demonstrate that the ordinary surface cannot independently produce the same externally observable protected outcome.

## 15. Required External Reviewer Deliverable

| Component | Process / UID | Interface | Target | Effect | Protected? | Fence Required? | Can Produce X? | Evidence | Status |
|---|---|---|---|---|---|---|---|---|---|
| Protected adapter | — | commit | authoritative target | X | YES | YES | TBD | deployment evidence | TBD |
| Ordinary dispatcher | — | UNIX socket | filesystem root | WRITE | NO | NO | TBD | deployment evidence | TBD |
| Database connection | — | DB | TBD | mutation | TBD | TBD | TBD | deployment evidence | TBD |
| Helper process | — | IPC/subprocess | TBD | TBD | TBD | TBD | TBD | deployment evidence | TBD |

The matrix should be exhaustive for the declared deployment boundary.

## 16. Reviewer Independence

A11 should be performed by a reviewer who did not author the protected-boundary implementation.

The reviewer should begin with:

> Where can X happen without DAR?

The burden is on the boundary claim to survive attempts to find an alternate path.

## 17. Final A11 Decision Rule

```
                         PROTECTED OUTCOME X
                                  |
                    +-------------+-------------+
                    |                           |
              FENCED SURFACE              OTHER SURFACES
                    |                           |
                    |                     Can produce X?
                    |                       /       \
                    |                     YES        NO
                    |                      |          |
                    |                    FAIL       continue
                    |
                    v
             exhaustive review
                    |
             +------+------+
             |             |
          evidence      insufficient
          complete        evidence
             |             |
           PASS       NOT PROVEN
```

The A11 invariant is:

> **Once refusal(X) is authoritative, no reachable execution surface outside the protected commit mechanism can produce X.**

That invariant is the object of A11.
