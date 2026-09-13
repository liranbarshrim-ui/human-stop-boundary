"""Emit a deterministic evidence manifest for a DAR conformance run."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec"
FILES = [
    SPEC / "boundary_manifest_v1.json",
    SPEC / "CONFORMANCE.md",
    SPEC / "ATTACK_CATALOG_v1.md",
    SPEC / "FORMAL_PROPERTY.md",
    SPEC / "ASSUMPTION_STATUS.md",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest():
    return {
        "format": "DAR-CONFORMANCE-EVIDENCE-1",
        "spec_files": {str(p.relative_to(ROOT)): sha256(p) for p in FILES},
        "property": "VALID_REFUSAL => NO_PROTECTED_COMMIT",
        "classification": ["PASS", "FAIL", "OUT-OF-SCOPE", "AMBIGUOUS"],
    }


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
