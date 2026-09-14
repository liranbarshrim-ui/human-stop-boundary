import json
import os
import sys
import urllib.request

from dar_v36_14.dar.rekor_anchor import RekorMonotonicAnchor


SERVER = os.environ.get("DAR_REKOR_URL", "https://rekor.sigstore.dev")


def fetch_entry(uuid: str) -> dict:
    req = urllib.request.Request(f"{SERVER.rstrip('/')}/api/v1/log/entries/{uuid}")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main() -> None:
    anchor = RekorMonotonicAnchor(SERVER)
    first = anchor.publish(b"DAR-v37-anchor-test/refusal/one")
    second = anchor.publish(b"DAR-v37-anchor-test/refusal/two")

    assert second.log_index > first.log_index, (first, second)
    assert second.tree_size >= second.log_index + 1, (second,)
    assert fetch_entry(first.uuid), first
    assert fetch_entry(second.uuid), second

    floor = anchor.floor()
    assert floor == second.log_index, (floor, second)
    try:
        anchor.advance_to(first.log_index)
    except ValueError:
        pass
    else:
        raise AssertionError("external anchor accepted rollback")

    evidence = {
        "evidence_type": "external-rekor-monotonic-anchor",
        "server": SERVER,
        "verdict": "PASS",
        "checks": {
            "first_entry_retrievable": "PASS",
            "second_entry_retrievable": "PASS",
            "strict_log_index_increase": "PASS",
            "tree_size_consistent": "PASS",
            "local_floor_matches_external_index": "PASS",
            "rollback_rejected": "PASS",
        },
        "first": {
            "uuid": first.uuid,
            "log_index": first.log_index,
            "tree_size": first.tree_size,
            "digest": first.digest,
        },
        "second": {
            "uuid": second.uuid,
            "log_index": second.log_index,
            "tree_size": second.tree_size,
            "digest": second.digest,
        },
    }
    print(json.dumps(evidence, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"evidence_type": "external-rekor-monotonic-anchor", "verdict": "FAIL", "error": repr(exc)}), flush=True)
        raise
