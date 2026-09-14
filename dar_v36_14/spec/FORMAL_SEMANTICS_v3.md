# DAR Formal Semantics v3 — Refusal and Protected Effect

## Status

**PRE-REGISTERED / CORE SEMANTIC DEFINITION**

This document freezes the meaning of `valid_refusal` and `protected_commit` for the DAR v3 research claim. It deliberately separates evidence produced by the DAR mechanism from the external effect DAR is intended to prevent.

## 1. Valid refusal

A `valid_refusal(r,e)` is not an epoch increment by itself.

A refusal is valid only when all of the following hold:

1. **Named principal** — the refusal identifies an authorized human principal.
2. **Authentication** — the principal's authority is authenticated by the deployment's declared refusal-authentication mechanism.
3. **Target binding** — the refusal is bound to a specific protected effect instance or declared effect identity.
4. **Durable acceptance** — the enforcement boundary durably records acceptance of the refusal before treating it as effective.
5. **Ordering** — the refusal is ordered before the protected commit it is intended to prevent.
6. **Scope** — the refusal concerns an effect inside the declared protected-effect boundary.

An epoch transition may be an implementation consequence of a valid refusal, but an epoch transition alone is **not** evidence that a named human refused an effect.

Formally:

```text
valid_refusal(r,e)
  := named(r)
   ∧ authenticated(r)
   ∧ bound_to(r,e)
   ∧ durably_accepted(r)
   ∧ in_scope(r,e)
```

The temporal ordering condition is represented separately:

```text
r ≺ protected_commit(e)
```

## 2. Protected commit

`protected_commit(e)` is the externally observable, irreversible effect whose prevention is the subject of the DAR claim.

It is **not** defined as:

- a DAR journal `COMMITTED` record;
- a Store mutation;
- capability consumption;
- an epoch transition;
- a successful call to an internal adapter by itself.

Those are mechanism-level evidence and state transitions. They may provide evidence about whether a protected effect was authorized or attempted, but they are not equivalent to the external outcome.

Examples of protected effects include, depending on the declared deployment boundary:

- an irreversible database mutation;
- an externally accepted transaction;
- an externally published message that causes an irreversible downstream action;
- an external API operation whose semantics make the outcome irreversible;
- a filesystem state transition only when that transition itself is the declared irreversible effect.

The deployment manifest MUST identify which external effect is the protected effect. A syscall-level or adapter-level proxy MUST NOT silently be presented as equivalent to the external outcome.

## 3. Core property

The DAR v3 property is:

```text
valid_refusal(r,e)
∧ r ≺ protected_commit(e)
∧ A1
∧ A9
⇒ ¬reachable(protected_commit(e))
```

This is intentionally conditional. It does not claim that every real-world consequence of every system action is prevented merely because a local DAR WRITE was denied.

## 4. Crash semantics

A crash after an external protected effect has occurred but before DAR durably records `COMMITTED` is treated as an **external-effect ambiguity**, not as a successful refusal.

If the external effect has occurred, then:

```text
protected_commit(e) = true
```

regardless of whether DAR later records `REFUSED` during recovery.

Therefore a recovery record of `REFUSED` MUST NOT be interpreted as proof that the external protected effect did not occur.

A deployment claiming prevention of such effects MUST additionally provide an external transaction/commit protocol, idempotent atomic adapter semantics, or an explicitly bounded compensating-action protocol. A local journal alone is insufficient evidence of external non-occurrence.

## 5. Evidence hierarchy

The following distinctions are mandatory:

| Observation | Meaning |
|---|---|
| capability consumed | authorization state changed |
| epoch advanced | generation barrier changed |
| `PREPARED` | DAR recorded an in-progress effect |
| `COMMITTED` | DAR recorded local completion/commit evidence |
| `REFUSED` | DAR recorded refusal of the pending local effect |
| external protected effect | the protected outcome actually occurred |

Only the final row determines whether the protected effect occurred.

## 6. Human-authority boundary

The implementation MUST NOT describe an epoch increment as a cryptographically authenticated human refusal unless a separate refusal-authentication protocol establishes that fact.

Until such a protocol exists, implementation-level claims MUST use terms such as:

- `epoch barrier`;
- `refusal state transition`;
- `store generation change`;

and MUST NOT silently equate these with `named human refusal`.

## 7. A1 consequence

A1 is satisfied only if the independent completeness audit covers every path capable of producing the declared **protected outcome**, not merely every path capable of invoking a particular `WRITE` syscall or DAR adapter.

If the audit covers only a local write primitive while the actual protected effect is a downstream database transaction, queue-triggered action, external API effect, subprocess action, or other causal chain, A1 is incomplete for the stronger outcome claim.

## 8. Claim boundary

DAR therefore claims only the property that the deployment can actually define, audit, authenticate, and observe.

It does not claim:

- universal human control;
- universal prevention of irreversible consequences;
- that a DAR `REFUSED` record proves the world did not change;
- that an epoch transition is itself a named human act;
- complete mediation beyond the independently audited protected-effect boundary.
