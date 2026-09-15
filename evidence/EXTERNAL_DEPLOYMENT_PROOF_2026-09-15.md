# DAR External Enforcement Evidence — 2026-09-15

## Scope

This record documents a live Make deployment test of the DAR Decision Gate against an external Google Sheets state mutation.

This is **deployment evidence for the tested path**, not a universal security proof and not a full DAR v2 conformance result.

## Controlled test

Protected external effect: write `Evidence!A1` in Google Sheets.

### ALLOW

Input:

- Decision: `ALLOW`
- Evidence ID: `DAR-EXT-ALLOW-20260915-06`

Make execution:

- Execution ID: `9a9f5456da324e30a9d7c4fe3cf0ecc0`
- Status: `success`
- Started: `2026-09-15T02:52:52.874Z`

Observed enforcement:

- `google-sheets:updateCell` was invoked exactly once.
- Target: `Evidence!A1`
- Value written: `DAR ALLOW — DAR-EXT-ALLOW-20260915-06`
- Google Sheets response reported `updatedRows: 1`, `updatedColumns: 1`, `updatedCells: 1`.

Independent read-back:

- A separate `google-sheets:getCell` execution read `Evidence!A1`.
- Returned value: `DAR ALLOW — DAR-EXT-ALLOW-20260915-06`

### DENY

Input:

- Decision: `DENY`
- Evidence ID: `DAR-EXT-DENY-20260915-03`

Make execution:

- Execution ID: `8836fb0d6bcd4ada8356305515034a3c`
- Status: `success`
- Output: `DENY_BLOCKED`
- Started: `2026-09-15T02:54:00.700Z`

Observed enforcement:

- Only the StartSubscenario and DENY ReturnData modules ran.
- `google-sheets:updateCell` was not invoked.
- Total operations: `0`.

## Result

For this deployed path and tested external effect:

`ALLOW -> external mutation -> read-back confirms mutation`

`DENY -> external mutation module not invoked`

A concise formalization is:

`E = 1[D = ALLOW]`

and, for the tested external state transition:

`D = ALLOW => ΔS != 0`

`D = DENY => no invocation of E`

The stronger universal statement `P(E_external | DENY) = 0` is **not claimed** by this single-path experiment. Establishing that requires independent interface/escape-path completeness evidence over every path capable of producing the protected effect.

## Reproduction notes

The test used the live Make scenario `DAR — Decision Gate Proof 01` and an authorized Google Sheets connection. The dedicated spreadsheet was identified by its spreadsheet ID and its actual sheet title `Evidence` rather than the initially assumed `Sheet1`.

Historical failures are not erased: earlier executions failed first on missing `valueInputOption` and then on the invalid `Sheet1!A1` range. The successful run above followed correction of those configuration issues.

## Evidence status

**PASS — bounded external enforcement demonstration for the declared test path.**

**Not claimed:** production certification, universal AI control, independent interface completeness, or full DAR v2 PASS.
