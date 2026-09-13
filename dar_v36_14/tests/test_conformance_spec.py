import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec"


def test_boundary_manifest_is_pre_registered():
    m = json.loads((SPEC / "boundary_manifest_v1.json").read_text())
    assert m["spec_version"] == "BRB-1.0"
    assert m["status"] == "pre-registered"
    assert m["rules"]["no_post_hoc_boundary_change"] is True
    assert m["rules"]["ambiguous_is_not_pass"] is True


def test_classification_is_closed():
    m = json.loads((SPEC / "boundary_manifest_v1.json").read_text())
    assert set(m["classification"]) == {"PASS", "FAIL", "OUT-OF-SCOPE", "AMBIGUOUS"}


def test_protected_property_is_explicit():
    m = json.loads((SPEC / "boundary_manifest_v1.json").read_text())
    assert m["property"] == "VALID_REFUSAL => NO_PROTECTED_COMMIT"
    assert "WRITE" in m["effective_boundary"]["protected_effect_classes"]
