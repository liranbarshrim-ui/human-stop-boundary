# DAR v37 — Gap Closure Plan v1

## Purpose

This file turns the remaining DAR v37 evidence gaps into concrete, reproducible work items without promoting internal repository inspection to external PASS.

## Active run

The 10,000-round external black-box stress run is already executing against the Render reference deployment. Do not restart, redeploy, or mutate the target deployment while this run is active. Record the final completed-round count, worker count, stage, exit condition, and machine-readable verdict when the process terminates.

## Gate A — 10K stress

Required final evidence:

- rounds = 10,000;
- workers = 32;
- every round completed;
- no refusal/commit both-winner outcome;
- fresh idempotency key cannot bypass terminal refusal;
- legitimate commit remains committed against later refusal;
- machine-readable verdict = PASS.

A partial run is evidence of execution progress only, not Gate A PASS.

## Gate B — crash/restart

Existing repository suite covers registered crash-boundary scenarios. Remaining deployment-level confirmation must include an actual service restart/recreation followed by refusal-state verification and pending-intent reconciliation under the declared adapter contract.

## Gate C — independent interface / escape audit

Required independent checks on the frozen deployment:

1. unauthorized OS identity attempts to produce the protected WRITE;
2. alternate IPC/socket/pipe/queue/shared-memory paths;
3. helper/child-process delegation;
4. direct adapter and deprecated/importable interface invocation;
5. startup/recovery/reconciliation after refusal;
6. descriptor/path substitution and TOCTOU;
7. network/plugin/side-channel routes capable of producing the protected outcome;
8. local-state rollback followed by a fresh protected commit attempt.

Repository-authored tests may prepare the harness but cannot certify this gate.

## External monotonic anchor

Rekor may witness transitions, but it is not the decisive serialization authority. The decisive authority must remain external to the DAR process and local rollback domain and must atomically reject protected commits after terminal refusal. Required evidence covers monotonicity, refusal dominance, crash persistence, replay resistance, and independent verification.

## Gate D — second provider

A second independently administered infrastructure provider must reproduce the frozen protocol. A second deployment on the same provider does not satisfy this requirement. Provider-specific shortcuts are not permitted.

## Evidence rule

No gap is marked PASS merely because a test, document, or source inspection exists. Each gate is marked PASS only when its preregistered evidence condition is actually demonstrated.

## Current disposition

- Gate A: RUNNING / pending final result.
- Gate B: repository suite present; deployment-level restart/reconciliation evidence pending.
- Gate C: independent deployment-level audit pending.
- External monotonic anchor: protocol defined; decisive external serialization evidence pending.
- Gate D: second-provider reproduction pending.
