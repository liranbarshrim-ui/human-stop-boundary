#!/usr/bin/env python3
"""Self-authored differential A-08 reproduction.

This script intentionally does not import DAR implementation internals. It
reimplements the public canonicalization/HMAC profile to detect implementation
or encoding drift. It is differential evidence, not an independently authored
replication by an unrelated team.
"""
import hashlib
import hmac
import json
import math
import unicodedata


def normalize(value):
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError("non-integral or non-finite float")
        return int(value)
    if isinstance(value, dict):
        out = {}
        for key in sorted(value):
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in out:
                raise ValueError("duplicate key after NFC normalization")
            out[normalized_key] = normalize(value[key])
        return out
    if isinstance(value, (list, tuple)):
        return [normalize(x) for x in value]
    raise TypeError(type(value).__name__)


def canonical_bytes(value):
    return json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def params_digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def capability_mac(secret, capability_id, principal, effect_class, digest):
    material = "|".join([capability_id, principal, effect_class, digest]).encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


def reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON object key")
        out[key] = value
    return out


def main():
    secret = b"self-authored-a08-test-secret"
    capability_id, principal, effect_class = "cap-a08-diff", "alice", "WRITE"
    issued = {"path": "a08.txt", "data": "authorized"}
    substituted = {"path": "a08.txt", "data": "attacker"}
    issued_digest = params_digest(issued)
    mac = capability_mac(secret, capability_id, principal, effect_class, issued_digest)
    assert issued_digest == params_digest({"data": "authorized", "path": "a08.txt"})
    assert issued_digest != params_digest(substituted)
    forged = capability_mac(secret, capability_id, principal, effect_class, params_digest(substituted))
    assert not hmac.compare_digest(mac, forged)
    assert canonical_bytes({"text": "é"}) == canonical_bytes({"text": "e\u0301"})
    try:
        params_digest({"x": 1.5})
    except ValueError:
        pass
    else:
        raise AssertionError("non-integral float was accepted")
    try:
        json.loads('{"a":1,"a":2}', object_pairs_hook=reject_duplicate_keys)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate JSON key was accepted")
    try:
        params_digest({"é": 1, "e\u0301": 2})
    except ValueError:
        pass
    else:
        raise AssertionError("Unicode-colliding keys were accepted")
    print("A-08 self-authored differential reproduction: PASS")
    print(f"issued_params_digest={issued_digest}")
    print("post-issuance substitution: REJECTED")
    print("NFC-equivalent strings: SAME DIGEST")
    print("duplicate JSON keys: REJECTED")
    print("non-integral float: REJECTED")


if __name__ == "__main__":
    main()
