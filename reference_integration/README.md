# Reference Staging Deployment Integration

**Parent baseline (frozen, unmodified):** `b0fc0f8f0d719e80a00b27a789ec08c8f5131a81`

This branch adds a **reference integration only**. It does not change the A11 status of the frozen baseline.

## Purpose

Connect the existing protected-outcome path to one concrete, externally observable staging effect:

```
issue_protected
  → execute_protected
  → protected_commit
  → StagingDeploymentAdapter (fence/refusal checks)
  → mint_deploy_token (HMAC)
  → POST /staging/deploy (authorization required)
  → GET /staging/status/<deployment_id>
```

## Deploy authorization

`POST /staging/deploy` requires `deploy_authorization`:

- HMAC-SHA256 over
  `DEPLOY|deployment_id|artifact_digest|fence_epoch|idempotency_key|issued_at|expires_at`
- Token is minted only inside `StagingDeploymentAdapter.commit` after local fence and refusal checks
- Unauthenticated or invalid-MAC requests receive **401**

`POST /staging/refuse` publishes terminal refusal to staging (MAC-authenticated).
Staging rejects deploy for a refused `deployment_id` with **403 terminal_refusal**.

## Identity model

| Field | Binding |
|-------|---------|
| `artifact_digest` | SHA-256 of artifact bytes |
| `deployment_id` | SHA-256(JSON{artifact_digest, staging_target, label})[:32] |
| `outcome_key` | equals `deployment_id` |
| `effect_id` | SHA-256("effect:"+deployment_id)[:6] |

## Layout

| Path | Role |
|------|------|
| `identity.py` | Deterministic deployment / outcome identity |
| `staging_auth.py` | Mint / verify deploy tokens |
| `staging_server.py` | Isolated local staging HTTP service |
| `staging_adapter.py` | `FencedEffectAdapter` → authorized staging deploy |
| `qualify.py` | Optional local A/B helper |

## Out of scope

- Production credentials or real external systems
- Changing frozen baseline claims
- Asserting A11 PASS for `b0fc0f8`
