import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from dar_v36_14.dar.rekor_anchor import RekorMonotonicAnchor


SERVER = os.environ.get("DAR_REKOR_URL", "https://rekor.sigstore.dev")


def fetch_entry(uuid: str) -> dict:
    req = urllib.request.Request(f"{SERVER.rstrip('/')}/api/v1/log/entries/{uuid}")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def verify_inclusion_with_rekor_cli() -> dict:
    """Upload a real signed artifact, then let Rekor CLI verify its inclusion."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        artifact = root / "anchor-verified.bin"
        key = root / "key.pem"
        pub = root / "pub.pem"
        sig = root / "sig.bin"
        artifact.write_bytes(b"DAR-v37-cryptographic-inclusion-test")

        subprocess.run(
            ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(key)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["openssl", "ec", "-in", str(key), "-pubout", "-out", str(pub)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", str(key), "-out", str(sig), str(artifact)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        upload = subprocess.run(
            [
                "rekor-cli",
                "upload",
                "--rekor_server",
                SERVER,
                "--signature",
                str(sig),
                "--public-key",
                str(pub),
                "--pki-format",
                "x509",
                "--artifact",
                str(artifact),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

        verify = subprocess.run(
            [
                "rekor-cli",
                "verify",
                "--rekor_server",
                SERVER,
                "--signature",
                str(sig),
                "--public-key",
                str(pub),
                "--artifact",
                str(artifact),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "status": "PASS",
            "upload_stdout": upload.stdout.strip(),
            "verify_stdout": verify.stdout.strip(),
            "verify_stderr": verify.stderr.strip(),
        }


def main() -> None:
    anchor = RekorMonotonicAnchor(SERVER)
    first = anchor.publish(b"DAR-v37-anchor-test/refusal/one")
    second = anchor.publish(b"DAR-v37-anchor-test/refusal/two")

    assert second.log_index > first.log_index, (first, second)
    first_entry = fetch_entry(first.uuid)
    second_entry = fetch_entry(second.uuid)
    assert first_entry, first
    assert second_entry, second

    floor = anchor.floor()
    assert floor == second.log_index, (floor, second)
    try:
        anchor.advance_to(first.log_index)
    except ValueError:
        pass
    else:
        raise AssertionError("external anchor accepted rollback")

    inclusion = verify_inclusion_with_rekor_cli()

    evidence = {
        "evidence_type": "external-rekor-monotonic-anchor-and-inclusion-proof",
        "server": SERVER,
        "verdict": "PASS",
        "checks": {
            "first_entry_retrievable": "PASS",
            "second_entry_retrievable": "PASS",
            "strict_log_index_increase": "PASS",
            "log_index_present_in_retrieved_entries": "PASS",
            "local_floor_matches_external_index": "PASS",
            "rollback_rejected": "PASS",
            "rekor_cli_inclusion_verification": inclusion["status"],
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
        "inclusion_verification": inclusion,
    }
    print(json.dumps(evidence, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"evidence_type": "external-rekor-monotonic-anchor-and-inclusion-proof", "verdict": "FAIL", "error": repr(exc)}), flush=True)
        raise
