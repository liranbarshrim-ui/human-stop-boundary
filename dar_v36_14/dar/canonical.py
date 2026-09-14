"""Deterministic canonicalization for capability-bound protocol identities."""
import hashlib
import json
import math
import re
import unicodedata

class CanonicalizationError(ValueError):
    pass

# Protocol identities are opaque lowercase-hex tokens. Visual/confusable
# mappings are intentionally not attempted: the protocol accepts one syntax.
_OPAQUE_KEY_RE = re.compile(r"^[0-9a-f]+$")

def _canonical_opaque_key(value, name):
    if not isinstance(value, str) or not value:
        raise CanonicalizationError(f"{name} must be a non-empty string")
    normalized = unicodedata.normalize("NFC", value)
    if not _OPAQUE_KEY_RE.fullmatch(normalized):
        raise CanonicalizationError(f"{name} must be lowercase hexadecimal [0-9a-f]+ after NFC normalization")
    return normalized

def canonical_effect_id(value):
    return _canonical_opaque_key(value, "effect_id")

def canonical_outcome_key(value):
    """Canonical identity of the protected external outcome.

    This is deliberately distinct from effect_id. An effect_id identifies a
    protocol invocation; outcome_key identifies the external world-state
    outcome that the refusal is intended to fence. It must therefore be
    supplied by the deployment/business protocol rather than inferred from
    an invocation label or blindly derived from parameters.
    """
    return _canonical_opaque_key(value, "outcome_key")

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
        out = {}
        for key in sorted(value):
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in out:
                raise CanonicalizationError(f"duplicate object key after NFC normalization: {normalized_key!r}")
            out[normalized_key] = _normalize(value[key])
        return out
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
