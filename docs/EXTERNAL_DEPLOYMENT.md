# External deployment evidence

DAR's strongest claim requires an external authority, not only an in-process test or a second process on the same CI runner.

## Render deployment

1. In Render, choose **New → Blueprint**.
2. Select `liranbarshrim-ui/human-stop-boundary`.
3. Render reads the repository's `render.yaml`.
4. The service starts `dar_v36_14/external_authority_server.py` and exposes `/health`, `/state`, `/fence`, `/refuse`, and `/commit`.
5. Copy the public HTTPS service URL, for example `https://<service>.onrender.com`.

## Verify it from GitHub Actions

Create a repository Actions secret named:

`DAR_EXTERNAL_AUTHORITY_URL`

Set its value to the public service URL. Do not commit the URL as a secret if it contains credentials; this service currently needs no credentials.

Then run **DAR External Authority Evidence** from the Actions tab. The workflow runs the black-box verifier and uploads `external-authority-evidence.json`.

The verifier checks:

- health endpoint;
- commit-before-refusal is not retroactively undone;
- refusal retry is idempotent;
- refusal blocks commit;
- a new idempotency key cannot bypass a terminal refusal;
- numeric fence rollback is rejected;
- authoritative state is observable.

## Evidence boundary

A successful run is **deployment-level black-box evidence**. It is not automatically production certification. Production certification additionally requires independent verification of hosting, persistence, access control, deployment identity, and the assumptions in the DAR Outcome-Fenced Safety registry.
