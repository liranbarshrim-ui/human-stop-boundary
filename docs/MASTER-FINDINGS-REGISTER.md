# DAR Master Findings Register

**Status:** Working cumulative register  
**Branch:** `auth-escape-01-patch`  
**Purpose:** Preserve the cumulative findings from the current DAR evidence/review cycle without silently dropping open findings or converting scoped evidence into blanket certification.

> **Counting note:** The request that initiated this register said “all eight findings,” but enumerated **nine** distinct findings. This register therefore records all nine rather than silently omitting one.

## Status legend

- **CLOSED — SCOPED:** Closed only for the explicitly tested/evidenced scope; not a blanket certification of the broader gate set.
- **CLOSED:** The specific finding has been resolved and the available evidence supports closure.
- **OPEN:** Active finding requiring further work or a decision.
- **DECISION REQUIRED:** A real semantic/specification decision is pending; it must not be hidden by implementation or test changes.
- **VERIFIED CODE CONDITION:** Direct source inspection establishes the stated code condition; live exploit/evidence execution may still be pending.

---

## 1. AUTH-ESCAPE-01 — CLOSED — SCOPED

**Title:** Enforce wire protocol v2 authorization boundary.

**Closure basis:** Dedicated Evidence Run #6 (`35302067586`) checked out the exact claimed SHA `69b61c60e620ee38c6dbce1039f024d2904b43b5` and executed the intended workflow definition from `auth-escape-01-patch` with:

```text
PYTHONPATH=. pytest -v -s tests/test_auth_escape_01.py
```

Result: `13 passed in 6.18s`.

Raw stdout included the primary valid-transport/no-intent mutation case:

```text
RAW_AUTH_ESCAPE_01_COMMIT status=401 body={"error": "missing_authority_intent", "ok": false}
```

Permanent artifact: `auth-escape-01-evidence-35302067586` (artifact ID `10529553901`).

**Scope statement:** CLOSED for the tested scenario set, with full raw HTTP evidence for the primary valid-transport/no-intent mutation case. This is **not** a certification of the broader DAR gate set.

**Methodological record:** The evidence run established the need to bind `workflow_dispatch` provenance to the code under test: the workflow-definition ref and the claimed SHA must reference the same commit.

---

## 2. FENCE-GRIEFING-01 — OPEN

**Title:** Prevent arbitrary forward fence jumps without breaking legitimate refusal/recovery semantics.

**Acceptance direction:**

1. Define the valid epoch transition explicitly. `current + 1` is the default candidate test, but implementation must first be checked against existing `fence()` / `refuse()` semantics rather than assumed.
2. Arbitrary jumps (`current + N`, N > 1) must be rejected if the reviewed contract establishes strict sequential advancement.
3. Regression must traverse the HTTP boundary, not only a direct/component `fence()` call.
4. Rejection must not mutate protected state.
5. A legitimate stale-client recovery/retry path is mandatory. The security fix must not create an avoidable legitimate-client denial-of-service condition. The recovery path must obtain authoritative current state through an authorized path, recalculate safely, and retry under the defined epoch contract.
6. Determine explicitly whether the wire protocol must change. No wire-protocol change may be assumed; if the review shows one is required, stop and re-scope as a breaking protocol change before implementation.
7. Evidence must include exact claimed SHA, exact checked-out SHA, matching workflow-definition ref, explicit test command, exit code, raw stdout/stderr, raw HTTP status/body for the jump scenario, proof of unchanged state on rejection, and a permanent artifact.

**Critical compatibility point:** Current code does **not** enforce strict sequential advancement in `PostgresAuthority.fence()`: it rejects only `epoch < current`, rejects terminal refusal, and otherwise writes the supplied epoch. `PostgresAuthority.refuse()` likewise rejects only `epoch < current`; its fence update uses `GREATEST(current, epoch)`. Therefore `current + 1` must be treated as a candidate contract to validate, not as an already-established invariant.

### Parameter Binding Gap — VERIFIED CODE CONDITION

**Status:** `VERIFIED CODE CONDITION` via independent direct fetch of `dar_v36_14/external_authority_server.py` at SHA `69b61c60e620ee38c6dbce1039f024d2904b43b5`. Independent live HTTP exploit/evidence execution remains pending.

**Observed condition:** `_verify_intent()` extracts and MAC-verifies `authority_intent["epoch"]`, while `do_POST()` subsequently executes the operation using the separate outer `data["epoch"]`. `_protected()` calls `_verify_transport()` and then `_verify_intent()`, but the reviewed path contains no comparison binding the outer epoch to the signed inner epoch before the operation is dispatched. The condition is present in both the PostgreSQL `authority.*` dispatch path and the in-memory fallback path.

**Independent verification:** The raw file was fetched directly from GitHub outside the ChatGPT citation layer using the exact commit SHA. This independently confirmed the source condition.

**Required next evidence:** Run the HTTP-boundary regression/exploit test that signs an intent for epoch A, submits outer epoch B, and records the HTTP response plus `/state` before/after. Do not implement the fix before this execution unless a separate safety decision explicitly requires it.

**Important scope distinction:** The code condition is verified; exploit-in-practice is not yet classified as empirically demonstrated until the live HTTP test produces the expected result. No broader claim about all credential configurations should be made from the source condition alone.

**Evidence test added:** `dar_v36_14/tests/test_auth_escape_01_parameter_binding_gap.py`.

**Evidence workflow added:** `.github/workflows/parameter-binding-gap-evidence.yml`.

**Latest evidence-preparation commit:** `876da7271f4e6b7b08711d69da2d15a80c752632`.

**Workflow requirement:** The evidence workflow requires `claimed_sha` and checks that the checked-out SHA exactly equals it; it also records the workflow-file hash, command output, exit code, and uploads raw stdout/stderr/provenance as an artifact.

**Execution limitation:** The available GitHub connector can create the workflow and inspect workflow runs, but does not expose a workflow-dispatch/write action. Therefore no live GitHub evidence run is claimed until the workflow is actually dispatched and its run/artifact are independently observable.

---

## 3. RECON-VIA-STATE-01 — CLOSED

**Title:** Reconciliation/state-authority path finding.

**Status:** CLOSED based on the completed review/evidence cycle for this finding. Preserve the closure as scoped to the reviewed state/reconciliation behavior; do not use it to imply closure of unrelated authority-boundary findings.

---

## 4. ORPHANED-AUTH-LAYER-01 — OPEN

**Title:** Orphaned `RefusalAuthority` authentication layer.

The original internal MAC/authentication layer remains distinct from the wire protocol v2 authorization path and is not yet demonstrated as fully connected to the intended end-to-end authority boundary.

**Required disposition:** Keep open until its relationship to the live authorization path is explicitly demonstrated and evidenced.

---

## 5. A9-INTEGRATION-DISCONNECT-01 — OPEN

**Title:** A9 integration disconnect.

A9 remains an active integration finding. It must remain visible in the cumulative register until its required integration boundary and evidence are demonstrated.

**Required disposition:** Keep open; do not infer closure from AUTH-ESCAPE-01 evidence.

---

## 6. IDEMPOTENCY-MISMATCH — CLOSED

**Title:** Idempotency mismatch.

**Status:** CLOSED for the specific mismatch identified during the evening review, based on the corrective implementation/tests already validated in the project evidence cycle.

**Scope:** Closure applies to the identified mismatch; unrelated idempotency behavior must still be governed by the existing tests/contracts.

---

## 7. SSLMODE — CLOSED

**Title:** PostgreSQL SSL mode configuration mismatch.

**Status:** CLOSED for the identified configuration mismatch. Current PostgreSQL authority connection logic explicitly derives `DAR_DB_SSLMODE` and defaults to `require` when unset/blank.

**Scope:** This closes the identified sslmode configuration finding; it does not certify every deployment environment's TLS configuration.

---

## 8. BR-B3 — DECISION REQUIRED / OPEN

**Title:** Strong-outcome-fence registration status drift.

This is a real unresolved test/specification drift and must remain visible.

Current evidence shows a mismatch between the conformance test expectation and the boundary manifest status: the test expects `pre-registered`, while the manifest was later synchronized to `frozen-evidence-package`.

**Decision required:** Determine the intended normative status and then update the test/spec/documentation consistently. Do not close, ignore, or suppress the failing test merely to make CI green.

**Rule:** BR-B3 remains open until an explicit semantic decision is recorded and the implementation/spec/test state is reconciled.

---

## 9. CI-DEPENDENCY-GAP-01 — CLOSED

**Title:** Missing `psycopg` test dependency.

**Finding:** `psycopg` was absent from the test installation path, causing the PostgreSQL authority import to fail before AUTH execution in the dedicated evidence workflow.

**Resolution:** The test extra was updated to include `psycopg[binary]>=3` alongside `pytest>=8`. Subsequent CI/evidence execution installed the PostgreSQL driver successfully and AUTH-ESCAPE-01 executed to completion.

**Closure scope:** The dependency gap is closed for the repository's declared test-installation path. Production/runtime dependency choices remain a separate deployment concern.

---

## Evidence and governance rules

### SHA as evidentiary contract

When triggering `workflow_dispatch`, the **“Use workflow from” branch/ref** and the **`claimed_sha` input** must reference the same commit. Otherwise, the executed workflow definition may not match the code under test even when the workflow's checkout step correctly checks out the claimed SHA.

### Scoped evidence is not blanket certification

A finding may be marked **CLOSED — SCOPED** only when the exact tested scenario set and evidence chain are recorded. Passing a dedicated test file does not certify unrelated gate paths.

### Open findings must remain cumulative

Closing one finding must not remove or imply closure of other findings. In particular, the following remain explicitly open/active after AUTH-ESCAPE-01 closure:

- `FENCE-GRIEFING-01`
- `ORPHANED-AUTH-LAYER-01`
- `A9-INTEGRATION-DISCONNECT-01`
- `BR-B3` (decision required)

### Source condition vs exploit evidence

A source-level condition established by direct inspection is distinct from empirical exploit evidence. The register must not collapse these states. A finding can be `VERIFIED CODE CONDITION` while its live HTTP exploit remains unverified.

---

## Current register snapshot

| Finding | Status |
|---|---|
| AUTH-ESCAPE-01 | CLOSED — SCOPED |
| FENCE-GRIEFING-01 | OPEN — Parameter Binding Gap: VERIFIED CODE CONDITION; live exploit pending |
| RECON-VIA-STATE-01 | CLOSED |
| ORPHANED-AUTH-LAYER-01 | OPEN |
| A9-INTEGRATION-DISCONNECT-01 | OPEN |
| IDEMPOTENCY-MISMATCH | CLOSED |
| SSLMODE | CLOSED |
| BR-B3 | DECISION REQUIRED / OPEN |
| CI-DEPENDENCY-GAP-01 | CLOSED |
