#!/usr/bin/env bash
set -euo pipefail

EXPECTED_COMMIT="${DAR_A11_FROZEN_COMMIT:-b0fc0f8f0d719e80a00b27a789ec08c8f5131a81}"
ROOT="${DAR_A11_ROOT:-/opt/dar}"
OUT="${DAR_A11_RESULTS:-${ROOT}/audit-results}"

mkdir -p "$OUT"
cd "$ROOT"

actual_commit="$(git rev-parse HEAD 2>/dev/null || true)"
if [[ -z "$actual_commit" || "$actual_commit" != "$EXPECTED_COMMIT" ]]; then
  printf 'WRONG_FROZEN_COMMIT\nexpected=%s\nactual=%s\n' "$EXPECTED_COMMIT" "$actual_commit" | tee "$OUT/frozen_commit_check.txt"
  exit 2
fi
printf 'FROZEN_COMMIT_OK\n%s\n' "$actual_commit" | tee "$OUT/frozen_commit_check.txt"

{
  echo '=== timestamp ==='
  date --iso-8601=seconds
  echo '=== commit ==='
  git rev-parse HEAD
  echo '=== kernel ==='
  uname -a
  echo '=== identity ==='
  id
  echo '=== processes ==='
  ps -ef
  echo '=== sockets ==='
  ss -lntup || true
  echo '=== unix sockets ==='
  ss -lx || true
  echo '=== mounts ==='
  findmnt || true
  echo '=== users ==='
  getent passwd || true
  echo '=== groups ==='
  getent group || true
  echo '=== open files (best effort) ==='
  command -v lsof >/dev/null 2>&1 && lsof -nP || true
} > "$OUT/deployment_inventory.txt" 2>&1

python -m pip install --no-cache-dir '.[test]'

pytest -q tests/test_a11_harness.py 2>&1 | tee "$OUT/local_a11_harness.txt"

cat > "$OUT/A11_ENVIRONMENT_BASELINE.yaml" <<EOF
 audit_id: DAR-A11-AUDIT-2026-V3
 frozen_commit: "$actual_commit"
 frozen_commit_verified: true
 environment_bootstrap: completed
 local_a11_harness: supporting_evidence_only
 independent_runtime_audit: not_completed
 deployment_inventory: captured
 note: "Bootstrap prepares evidence; it does not establish A11 PASS."
EOF

printf '\nA11 audit environment prepared. Independent auditor must perform V1-V8 and preserve raw evidence.\n'
