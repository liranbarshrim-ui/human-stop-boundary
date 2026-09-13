#!/usr/bin/env python3
"""Independent A-08 reproduction.

This script intentionally does not import the DAR implementation. It implements
only the public canonicalization and HMAC profile needed to reproduce the
parameter-binding claim from the specification.
"""

import hashlib
import hmac
import json
import math


def normalize(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError("non-integral or non-finite float")
        return int(value)
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError("object keys must be strings")
        return {k: normalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [normalize(x) for x in value]
    raise TypeError(type(value).__name__)


def canonical_bytes(value):
    normalized = normalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def params_digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def capability_mac(secret, capability_id, principal, effect_class, params_digest_value):
    material = "|".join(
        [capability_id, principal, effect_class, params_digest_value]
    ).encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


def main():
    secret = b"independent-a08-test-secret"
    capability_id = "cap-a08-independent"
    principal = "alice"
    effect_class = "WRITE"

    issued = {"path": "a08.txt", "data": "authorized"}
    substituted = {"path": "a08.txt", "data": "attacker"}

    issued_digest = params_digest(issued)
    mac = capability_mac(secret, capability_id, principal, effect_class, issued_digest)

    assert issued_digest == params_digest({"data": "authorized", "path": "a08.txt"})
    assert issued_digest != params_digest(substituted)

    forged_mac = capability_mac(
        secret,
        capability_id,
        principal,
        effect_class,
        params_digest(substituted),
    )
    assert not hmac.compare_digest(mac, forged_mac)

    try:
        params_digest({"path": "a08.txt", "value": 1.5})
    except ValueError:
        pass
    else:
        raise AssertionError("non-integral float was accepted")

    print("A-08 independent reproduction: PASS")
    print(f"issued_params_digest={issued_digest}")
    print("post-issuance substitution: REJECTED")
    print("non-integral float: REJECTED")


if __name__ == "__main__":
    main()
