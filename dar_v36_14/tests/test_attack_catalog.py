from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = (ROOT / "spec" / "ATTACK_CATALOG_v1.md").read_text()

EXPECTED = [f"A-{i:02d}" for i in range(1, 13)]


def test_frozen_attack_catalog_contains_all_declared_attacks():
    for attack_id in EXPECTED:
        assert f"| {attack_id} |" in CATALOG


def test_catalog_forbids_post_hoc_rescue():
    assert "Create a new catalog version" in CATALOG
    assert "after seeing results" in CATALOG
