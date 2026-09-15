# Boundary Escape Audit v1

## Status

**AMBIGUOUS / NOT PASS** pending an independent deployment-level audit.

## Frozen boundary

The v2 manifest declares `WRITE` as the protected effect class, registers `PrivilegedDispatcher._open_write`, and defines `adapter_status=COMMITTED` as the commit event. The manifest also requires an independent interface-completeness audit and an external monotonic anchor.

## Repository-observed paths

- `PrivilegedDispatcher._open_write` — declared filesystem WRITE primitive.
- `PrivilegedDispatcher._apply` — dispatches WRITE to `_open_write`.
- `DispatcherClient.execute` — public client entry into `EffectGate`.
- `EffectGate.execute` — capability, replay, refusal, and parameter checks before execution.
- `EffectGate.execute_protected` — protected transaction/adapter commit path.
- `EffectGate.execute_recoverable` — recovery path that can finalize an adapter outcome after authoritative status checking.
- `EffectGate.reconcile_pending` — startup/recovery reconciliation path capable of invoking adapter commit.
- PostgreSQL authority — external refusal/fence/commit serialization state.
- Local `store.py` and `effect_journal.py` write DAR state/journal data using `os.write`; these are not automatically classified as the declared external WRITE outcome.
- subprocess/IPC/deployment helpers exist and must be covered by the deployment audit rather than excluded by source-level assertion.

## Adversarial scope still required

The independent audit must test, on the frozen deployment:

1. direct filesystem access by unauthorized OS identities;
2. alternate IPC/socket/pipe/queue paths;
3. helper or child-process delegation;
4. direct adapter invocation and deprecated/importable interfaces;
5. startup/recovery/reconciliation invocation after refusal;
6. descriptor/path substitution and TOCTOU attempts;
7. network/plugin/side-channel routes capable of producing the protected external outcome;
8. rollback of local state followed by a fresh protected commit attempt.

## Decision rule

No repository inspection result may be promoted to COMPLETE merely because the inspected source contains a registered gate. A v2 PASS requires an independent deployment-level completeness conclusion and the separate external monotonic-anchor condition.
