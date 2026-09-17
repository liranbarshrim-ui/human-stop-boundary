import json
import os
import subprocess
import urllib.request

from dar_v36_14.dar.rekor_anchor import RekorMonotonicAnchor

SERVER = os.environ.get("DAR_REKOR_URL", "https://rekor.sigstore.dev").rstrip("/")


def loginfo() -> dict:
    result = subprocess.run(
        ["rekor-cli", "loginfo", "--rekor_server", SERVER, "--format", "json"],
        check=True, capture_output=True, text=True, timeout=120,
    )
    return json.loads(result.stdout)


def fetch_entry(uuid: str) -> dict:
    req = urllib.request.Request(f"{SERVER}/api/v1/log/entries/{uuid}")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main() -> None:
    # A9: Deployment A is frozen and externally anchored.
    deployment_a = RekorMonotonicAnchor(SERVER)
    first = deployment_a.publish(b"DAR-A9-deployment-A/frozen-state")

    # A9: Deployment B advances the same external append-only witness.
    deployment_b = RekorMonotonicAnchor(SERVER)
    second = deployment_b.publish(b"DAR-A9-deployment-B/frozen-state")
    assert second.log_index > first.log_index

    # A9: restore the old Deployment A snapshot and query the external witness.
    restored_snapshot = {"anchor_uuid": first.uuid, "anchor_log_index": first.log_index}
    restored_entry = fetch_entry(restored_snapshot["anchor_uuid"])
    restored_index = int(restored_entry["logIndex"])
    info = loginfo()
    external_tree_size = int(info["ActiveTreeSize"])

    assert restored_index == first.log_index
    assert external_tree_size > second.log_index
    assert second.log_index > restored_index

    # The restored state is provably stale relative to the externally witnessed state.
    stale_restoration_detected = restored_index < second.log_index
    assert stale_restoration_detected

    # A current deployment's monotonic floor independently rejects the old value.
    try:
        deployment_b.advance_to(first.log_index)
    except ValueError:
        rollback_rejected = True
    else:
        rollback_rejected = False
    assert rollback_rejected

    evidence = {
        "evidence_type": "a9-deployment-specific-external-monotonic-rollback-restoration",
        "server": SERVER,
        "verdict": "PASS",
        "deployment_a": {"anchor_uuid": first.uuid, "log_index": first.log_index, "tree_size": first.tree_size},
        "deployment_b": {"anchor_uuid": second.uuid, "log_index": second.log_index, "tree_size": second.tree_size},
        "restored_deployment_a": restored_snapshot,
        "external_tree_size_after_restore": external_tree_size,
        "stale_restoration_detected": stale_restoration_detected,
        "rollback_rejected": rollback_rejected,
        "checks": {
            "deployment_a_anchor_persisted_externally": "PASS",
            "deployment_b_anchor_strictly_advanced": "PASS",
            "restored_old_anchor_retrievable": "PASS",
            "external_witness_remains_ahead_after_restore": "PASS",
            "stale_restoration_detected": "PASS",
            "numeric_floor_rollback_rejected": "PASS",
        },
        "scope_note": "Deployment-specific rollback detection against the external append-only witness. This is A9 evidence only; it does not prove A10 external commit serialization or system-wide interface completeness.",
    }
    print(json.dumps(evidence, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"evidence_type": "a9-deployment-specific-external-monotonic-rollback-restoration", "verdict": "FAIL", "error": repr(exc)}, sort_keys=True), flush=True)
        raise
