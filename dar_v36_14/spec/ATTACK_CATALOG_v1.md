# DAR Adversarial Attack Catalog v1

This catalog is frozen with Boundary Manifest BRB-1.0. Additions or exclusions after seeing results belong to a new catalog version.

| ID | Attack family | Intended property |
|---|---|---|
| A-01 | refusal-before-execution | refusal blocks commit |
| A-02 | refusal/execute race | refusal remains binding |
| A-03 | replay | consumed capability cannot commit again |
| A-04 | stale capability | prior authorization cannot cross refusal/epoch boundary |
| A-05 | rollback | restored state cannot resurrect authority |
| A-06 | alternate interface | protected effect cannot bypass registered gate |
| A-07 | confused deputy | caller cannot obtain another principal's effect |
| A-08 | parameter substitution | committed effect matches authorized parameters |
| A-09 | recovery replay | crash recovery cannot duplicate a committed effect |
| A-10 | journal tampering | inconsistent evidence is rejected |
| A-11 | adapter false-success | return value cannot substitute for authoritative commit status |
| A-12 | boundary ambiguity | unclear classification cannot become PASS |

## Execution rule

Run the catalog against a clean checkout of the exact commit containing the frozen specification. Record every test, including failures and ambiguous outcomes.

## No post-hoc rescue

A discovered bypass must not be reclassified by editing this catalog. Create a new catalog version and preserve the original result.
