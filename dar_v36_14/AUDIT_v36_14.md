# DAR v36.14 Verification Record

## Findings addressed

1. Recovery payloads were not previously bound to the durable `params_digest`.
2. Journal state transitions did not validate immutable intent fields.
3. Adapter `execute()` success was not sufficient evidence of external COMMITTED state.
4. Capability consumption and recoverable intent creation were separated across Store and journal files.
5. The live boundary test used a stale `/tmp/DAR_v36_5` path.
6. The original v36.10 README overstated `43 Python tests: PASS`; the accurate result was 42 pass and 1 skip.
7. Several governance/attenuation tests did not prove the intended guard was reached.
8. Recovery could return after an UNKNOWN final adapter status without proving commit.
9. Effect-state mutations did not advance the monotonic Store sequence, allowing a same-sequence snapshot rollback to bypass the anchor.
10. Pending intents had no explicit reconciliation operation after successful external execution followed by journal or cleanup failure.

## v36.14 controls

- Recovery recomputes and verifies `params_digest`.
- Journal rejects invalid ordering, duplicate PREPARED transitions and immutable-field changes.
- Recoverable intent is committed in the authenticated Store together with capability consumption.
- Journal PREPARED failure is fail-closed; no external effect is executed.
- COMMITTED is recorded only after authoritative adapter status confirms COMMITTED.
- Effect-state mutations advance the Store sequence, so an external monotonic anchor can detect rollback of consumed/pending effect state as well as authority state.
- `EffectGate.reconcile_pending()` reconciles durable pending intents against the adapter and validated journal state and removes them only after COMMITTED is established.
- Optional monotonic anchor detects Store rollback when the anchor is outside the rollback domain.
- IPC frame headers are read exactly, including fragmented stream headers.
- Live paths are derived from the checked-out artifact.
- Dedicated tests exercise the intended governance and permission-expansion guards.
- A live SIGKILL test verifies generation rotation and old-capability rejection.

## Reconciliation limitation

The current reconciliation mechanism is intentionally bounded. It is **post-success bookkeeping**, not autonomous retry recovery.

The durable pending intent contains an idempotency identity and `params_digest`, but the current implementation does not retain the original effect parameters. Therefore:

- if the adapter authoritatively reports `COMMITTED`, reconciliation can establish the committed outcome and clear the pending intent;
- if the adapter remains UNKNOWN or PREPARED, the pending intent remains pending;
- there is currently no timeout, stuck-state alert, retry counter, or autonomous retry operation;
- an UNKNOWN/PREPARED intent can therefore remain pending indefinitely and requires an external operational recovery decision if it never reaches COMMITTED.

This is a known limitation, not a claim of complete crash recovery.

## Evidence provenance

A separate process-level finding is **pasted-artifact drift**: content presented during an audit as a "current file" can differ from the actual repository state. In this audit cycle, instrumentation claims, version implementation claims and a pasted `policy.py` were all found to require repository verification rather than trust by presentation.

Accordingly, chat-pasted code is treated as **UNVERIFIED** until the exact repository version is checked out and compared.

The required evidence chain is:

**chat artifact → UNVERIFIED → fresh repository checkout → exact file comparison → execution → observed result → bounded claim**

A test result from one artifact/version must not be presented as evidence for another artifact/version merely because the filenames or descriptions appear equivalent.

## Verification

Current development checkout:

`PYTHONPATH=. pytest -q -v`

**Result: 60 passed, 1 skipped (61 collected).**

The single skip is the optional Landlock test because the host kernel returns `ENOSYS`.

Additional checks:

- `python -m pip install --no-deps --no-build-isolation .`: **PASS**.
- `python -m compileall -q dar tests`: **PASS**.
- Live two-UID boundary script: **PASS**.
- Live SIGKILL generation test: **PASS**.

## Claims not established

This is not an independent certification. It does not establish universal AI control, protection against an arbitrary privileged attacker, anti-rollback without an external trust anchor, or exactly-once semantics for arbitrary external systems.
