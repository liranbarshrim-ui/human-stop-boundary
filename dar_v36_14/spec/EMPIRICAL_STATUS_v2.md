# DAR Boundary Conformance — Empirical Attack Status v4

Status: **EVIDENCE PACKAGE — FROZEN GATES / EXTERNAL AUDIT PENDING**

This document is the current repository status for the DAR conformance package. Gate statuses below reflect the project-locked status and retained execution evidence. A PASS here does not mean universal AI control; the strong property remains conditional on the frozen deployment, declared boundary, authority contract, and threat model.

## Locked gate status

| Condition | Current status | Evidence / basis |
|---|---|---|
| A1 — protected-effect interface completeness | **PASS** | Project-locked status; retained interface/conformance evidence |
| A9 — external monotonic anchor | **PASS** | Deployment-specific external anchor / rollback evidence; project-locked status |
| A10 — same-authority fence/commit atomicity | **PASS** | Real PostgreSQL authority + adversarial race evidence; project-locked status |
| A12 — protected outcome idempotency | **PASS** | Real retry/crash/replay evidence; project-locked status |
| A13 — terminal external refusal state | **PASS** | Real PostgreSQL execution gate; workflow run 35170726030; retained artifact digest sha256:82443fb1d57b89ec2d18ab27ffa2a0664dedda4e6366550d588d3b4a072b4d23 |
| A11 — no alternate protected-outcome path | **PENDING INDEPENDENT AUDIT** | Requires deployment-level independent interface/escape audit |

## Existing execution evidence

The repository retains successful evidence for the 10K load/conformance path, PostgreSQL persistence, crash-boundary scenarios, restart persistence, and the locked A1/A9/A10/A12 project gates. These results are bounded to the tested deployment and code paths.

## A13 validation

`tests/test_a13_terminal_refusal_postgres.py` exercises the production `PostgresAuthority` against real PostgreSQL and verifies:

- terminal refusal blocks a same-epoch protected commit;
- a higher numeric fence update cannot clear terminal refusal;
- repeated identical refusal publication is idempotent;
- a stale refusal cannot overwrite a newer fence;
- a terminal refusal continues to block a fresh commit attempt.

`.github/workflows/a13-terminal-refusal-evidence.yml` runs this test against PostgreSQL 16 and retains a machine-readable evidence artifact. The retained successful run is 35170726030 and its artifact is `dar-a13-terminal-refusal-evidence`.

## A11 independent audit requirement

A11 is intentionally not self-certified by repository inspection. The required audit must independently enumerate every path capable of producing the protected outcome, including direct filesystem access, alternate IPC/socket/pipe/queue paths, child/helper delegation, direct adapter invocation, deprecated/importable APIs, startup/recovery/reconciliation, descriptor/path substitution and TOCTOU, subprocess/plugin/network side channels, and rollback followed by a fresh protected commit attempt.

The existing research issue for this work remains the deployment-level independent boundary audit. Repository tests are supporting evidence, not a substitute for independence.

## External audit status

An external adversarial technical audit has been requested. Until an independent reviewer produces a report, the repository must distinguish DAR-authored execution evidence from independent validation.

## Classification discipline

`PASS` is reserved for a gate whose declared evidence requirement has been satisfied under the frozen rules. Missing independent evidence remains `PENDING` or `AMBIGUOUS`; infrastructure failure is not silently converted into a conformance failure.

## Scope discipline

The strong property is conditional on the frozen deployment, external authority contract, declared boundary, and threat model. DAR does not claim universal AI control or system-wide complete mediation without independent interface evidence.
