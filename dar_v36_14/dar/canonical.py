"""Deterministic canonicalization for capability-bound parameters."""
import hashlib
import json
import math
import unicodedata

class CanonicalizationError(ValueError):
    pass

def _normalize(value):
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise CanonicalizationError("parameters must not contain non-integral floats")
        return int(value)
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise CanonicalizationError("parameter object keys must be strings")
        return {_normalize(k): _normalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(x) for x in value]
    raise CanonicalizationError(f"unsupported parameter type: {type(value).__name__}")

def canonical_bytes(value):
    try:
        normalized = _normalize(value)
        return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CanonicalizationError(str(exc)) from exc

def canonical_digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise CanonicalizationError(f"duplicate object key: {key!r}")
        out[key] = value
    return out

def parse_json_object(data):
    try:
        return json.loads(data, object_pairs_hook=reject_duplicate_keys)
    except (TypeError, ValueError, UnicodeError) as exc:
        if isinstance(exc, CanonicalizationError):
            raise
        raise CanonicalizationError(str(exc)) from exc
