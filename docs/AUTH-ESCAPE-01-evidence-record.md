# AUTH-ESCAPE-01 — Evidence Record

**Status:** PASS (scoped)

## Scope
PASS for the tested AUTH-ESCAPE-01 scenario set (13/13), with full raw HTTP evidence captured for the primary no-intent-mutation case. This is not certification of the broader DAR gate set or unrelated findings.

## Independent execution
- Evidence workflow run: `35302067586`
- Workflow branch/ref: `auth-escape-01-patch`
- Claimed SHA: `69b61c60e620ee38c6dbce1039f024d2904b43b5`
- Checked-out SHA: `69b61c60e620ee38c6dbce1039f024d2904b43b5`
- Result: 13/13 tests passed
- Raw evidence artifact: `auth-escape-01-evidence-35302067586` (artifact ID `10529553901`)

## Primary raw HTTP evidence
The authenticated transport-only `POST /commit` request without the required authority intent produced:

```text
RAW_AUTH_ESCAPE_01_COMMIT status=401 body={"error": "missing_authority_intent", "ok": false}
```

The response demonstrates rejection at the external HTTP authorization boundary rather than mutation through transport authentication alone.

## Evidence interpretation
This record establishes the tested HTTP authorization boundary behavior and the independent execution chain for the stated scenario set. It does not establish broader system-wide authorization, unrelated DAR gates, or closure of separately tracked findings.

## Explicitly remaining open
- FENCE-GRIEFING-01
- A9-INTEGRATION-DISCONNECT-01
- ORPHANED-AUTH-LAYER-01
- BR-B3

BR-B3 remains a separate conformance/spec decision: the current `boundary_manifest_v3.json` declares `status: frozen-evidence-package`, while the existing conformance test still expects `pre-registered`. This record does not resolve that discrepancy.
