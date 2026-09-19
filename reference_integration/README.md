# Reference Staging Deployment Integration

**Parent baseline (frozen, unmodified):** `b0fc0f8f0d719e80a00b27a789ec08c8f5131a81`

This branch adds a **reference integration only**. It does not change the A11 status of the frozen baseline.

## Purpose

Connect one concrete, externally observable staging effect to the actual DAR fenced transaction path:

```
caller-authenticated request
  → RefusalAuthority / protected refusal
  → protected_commit
  → StagingDeploymentAdapter (FencedEffectAdapter)
  → mint_deploy_token (HMAC)
  → POST /staging/deploy (authorization required)
  → GET /staging/status/<deployment_id>
```

A normal deployment is permitted at the initial fence epoch. A protected refusal advances the terminal external fence and is persisted by the staging service. A later protected commit must not create the staging effect after that refusal, including after the authority process is restarted.

## Deploy authorization

`POST /staging/deploy` requires `deploy_authorization`:

- HMAC-SHA256 bound to deployment identity, artifact digest, fence epoch, idempotency key and validity window
- Token is minted only inside `StagingDeploymentAdapter.commit` after its protected fence/refusal checks
- Unauthenticated or invalid authorization requests receive **401**
- A deployment whose external staging refusal is already recorded receives **403 terminal_refusal**

`POST /staging/refuse` publishes the terminal refusal to staging with a separate MAC-authenticated path.

## Identity model

| Field | Binding |
|-------|---------|
| `artifact_digest` | SHA-256 of artifact bytes |
| `deployment_id` | Deterministic deployment identity |
| `outcome_key` | equals `deployment_id` |
| `effect_id` | Deterministic effect identity |

## Runtime qualification

`two_uid_qualification.py` runs the reference topology with four distinct service identities:

- `darattacker`
- `darcaller`
- `darauthority`
- `darstaging`

It checks credential custody, normal deployment through DAR `protected_commit`, direct attacker access to staging and authority endpoints, protected refusal, post-refusal denial, and post-restart replay denial.

The generated `two_uid_evidence.json` is runtime evidence. Repository-authored unit tests are not substituted for this evidence.

## Layout

| Path | Role |
|------|------|
| `identity.py` | Deterministic deployment / outcome identity |
| `staging_auth.py` | Mint / verify deploy tokens |
| `staging_server.py` | Isolated local staging HTTP service |
| `staging_adapter.py` | `FencedEffectAdapter` → authorized staging deploy |
| `authority_effect.py` | Separate authority process using actual DAR protected transaction APIs |
| `caller_client.py` | Caller-authenticated request client |
| `two_uid_qualification.py` | Four-UID adversarial runtime qualification |

## Out of scope

- Production credentials or real external systems
- Changing frozen baseline claims
- Asserting A11 PASS for `b0fc0f8`
