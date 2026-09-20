# DAR Runtime Evidence Matrix

## Verified runtime qualifications

| Qualification | Scope | Result | Evidence |
|---|---|---|---|
| AUTH-ESCAPE-01 | Authentication boundary: fence/refuse/commit/state, replay, idempotency, legacy fallback | PASS | GitHub Actions run 35461182635; artifact SHA256 9b17ad06a20a54536ccdad46674f5094eb35cafaf6f8ca207c569198866bc68c |
| Reference staging / two-UID | Real isolated staging deployment; refusal blocks deployment; attacker denied across tested directions | PASS | GitHub Actions run 35462533957; evidence SHA256 e14214ce05a4095665b33c5b065ef58b2dd13b51c483e619de37c0d9bac163a9; artifact SHA256 293d87084bacbb54242e1a824199d381bfbdf4c8c9f6bc56ab640f25d7c075cf |
| Authorization forgery | Wrong-secret deploy/refusal, identity mutation, bounded secret guesses, cross-privilege reset, state tampering | PASS | Run #41 shown by supplied runtime screenshots; artifact created; prior bounded run evidence SHA256 8f98f01d49c0fe9dc012a0d870cd25aa95c8dddad0b5186def1bc6357e859e52 |
| Canonical 10K | 10,000 normal deployments + 10,000 refusal paths + 10,000 replay attempts | PASS | GitHub Actions run 35468644913; evidence SHA256 876e5d5fdc72f89b97f7d8ea659312ec527aa75745c5ee31d2abbc79ecaf414e; log SHA256 8da8d0e28cba4b0a3c123796956dc4fa3af99b9cee1595a49d17250b1b837dd0; artifact SHA256 41b8447a667777effe307157b576cd77d1c7fe3ca6c2fb019685365e029179f1 |
| Persistent Secret Restart | Same random secret bytes reused across restart; refusal survives restart; replay blocked; deploy secret cannot reset | PASS | Run 35501460060; artifact SHA256 6f364f2bed43beb1a8f6e2412b9b49d2d93fcdd38be80f08a7167c839f546808 |
| V1-V8 Runtime | Unauthorized identity, alternate transport, helper, direct/legacy, refusal/recovery, mutation/TOCTOU, side paths, rollback/replay/restart | PASS | Run 35471167207; evidence SHA256 bb56bc48b777337513443882daf68d8e070640cf293b7a46657ddc8a75e600b0; artifact SHA256 45b495bbaa12341614f6e3fbf9c319b44478d55aa40a32450f70ad0581f1d909 |

## Interpretation

These results establish runtime evidence for the tested reference integration and specified attack paths. They do not constitute universal security certification, production certification, or a claim that every possible implementation or effect path has been tested.

The reference integration protects a concrete isolated staging deployment effect. The qualification environment is intentionally bounded and excludes production credentials.

## Evidence rule

PASS means the corresponding qualification executed and produced the stated runtime result. Harness/environment failures are not converted into security PASS. Git commit SHA and evidence artifact SHA remain distinct identifiers.

## Remaining boundary

The runtime qualifications do not by themselves prove that every possible real-world external effect is governed by the same fence. Any new effect adapter or deployment topology requires its own reference qualification.
