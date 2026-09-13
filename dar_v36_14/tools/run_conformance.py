"""Run the portable conformance suite and emit a deterministic evidence record."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec"
TESTS = [
    "tests/test_conformance_spec.py",
    "tests/test_attack_catalog.py",
    "tests/test_boundary_negative.py",
    "tests/test_effect_refusal_property.py",
    "tests/test_attack_empirical.py",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    cmd = ["python", "-m", "pytest", "-q", *TESTS]
    completed = subprocess.run(cmd, cwd=ROOT, text=True)
    evidence = {
        "format": "DAR-CONFORMANCE-RUN-1",
        "spec_version": "BRB-1.0",
        "spec_hashes": {
            p.name: digest(p)
            for p in [
                SPEC / "boundary_manifest_v1.json",
                SPEC / "CONFORMANCE.md",
                SPEC / "ATTACK_CATALOG_v1.md",
                SPEC / "FORMAL_PROPERTY.md",
            ]
        },
        "exit_code": completed.returncode,
        "classification": "PASS" if completed.returncode == 0 else "FAIL",
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    raise SystemExit(completed.returncode)
