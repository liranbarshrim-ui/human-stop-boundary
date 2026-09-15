# Second-provider reproduction protocol

## Purpose

Reproduce the external DAR authority contract on a provider that is not Render. This is an evidence track, not a claim that a second deployment has already been completed.

## Required deployment shape

- One public HTTP service running `dar_v36_14/external_authority_server.py`.
- One PostgreSQL service/database controlled by the second provider.
- `DAR_PERSISTENCE_MODE=postgres`.
- `DATABASE_URL` referencing that provider's PostgreSQL service.
- `/health`, `/state`, `/fence`, `/refuse`, and `/commit` exposed exactly as the existing contract.

## Required evidence

Record the provider, service/deployment identifiers, database identifier, deployment commit SHA, and public base URL. The provider must be independently administered from Render; another Render service does not count.

Run the same black-box checks used by the Render evidence suite:

1. PostgreSQL persistence is reported by `/health`.
2. 250-round concurrent refusal/commit load completes.
3. No round produces both a committed effect and a terminal refusal.
4. A fresh idempotency key cannot bypass a winning refusal.
5. A winning commit remains observable after a later refusal attempt.
6. Restart/recovery does not erase a terminal refusal.

The machine-readable artifact must include the provider and deployment identifiers and must distinguish application-level failures from infrastructure saturation/timeouts.

## Safety boundary

Creating an account, connecting a repository, provisioning a database, or activating billing on a second provider requires explicit user authorization. Preparing this protocol and repository configuration does not provision external resources.

## Acceptance

The second-provider track is `PASS` only when the deployment exists and the required black-box evidence is independently observable. Repository configuration alone is not evidence of deployment.
