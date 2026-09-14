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
    "tests/test_atomic_fence_authority_v1.py",
    "tests/test_protected_outcome_fence_v1.py",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    cmd = ["python", "-m", "pytest", "-q", *TESTS]
    completed = subprocess.run(cmd, cwd=ROOT, text=True)
    differential = subprocess.run(
        ["python", "tools/self_authored_a08_differential.py"],
        cwd=ROOT,
        text=True,
    )
    evidence = {
        "format": "DAR-CONFORMANCE-RUN-2",
        "spec_version": "BRB-3.0",
        "spec_hashes": {
            p.name: digest(p)
            for p in [
                SPEC / "boundary_manifest_v3.json",
                SPEC / "CONFORMANCE.md",
                SPEC / "FORMAL_PROPERTY_v3_OUTCOME_FENCE.md",
                SPEC / "ASSUMPTIONS_v2.md",
            ]
        },
        "exit_code": completed.returncode,
        "self_authored_a08_differential_exit_code": differential.returncode,
        "classification": (
            "PASS"
            if completed.returncode == 0 and differential.returncode == 0
            else "FAIL"
        ),
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    raise SystemExit(0 if evidence["classification"] == "PASS" else 1)
