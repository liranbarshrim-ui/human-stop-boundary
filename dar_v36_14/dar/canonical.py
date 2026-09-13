"""Deterministic canonicalization for capability-bound parameters."""
import json
import math

class CanonicalizationError(ValueError):
    pass

def _normalize(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise CanonicalizationError('parameters must not contain non-integral floats')
        return int(value)
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise CanonicalizationError('parameter object keys must be strings')
        return {k: _normalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(x) for x in value]
    raise CanonicalizationError(f'unsupported parameter type: {type(value).__name__}')

def canonical_bytes(value):
    try:
        normalized = _normalize(value)
        return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CanonicalizationError(str(exc)) from exc

def canonical_digest(value):
    import hashlib
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
