"""Deterministic canonicalization for capability-bound parameters and effect identities."""
import hashlib
import json
import math
import re
import unicodedata

class CanonicalizationError(ValueError):
    pass

_EFFECT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")

def canonical_effect_id(value):
    """Return the canonical, unambiguous identity used by refusal/gate matching.

    Effect IDs are protocol identifiers, not free-form display text. NFC is
    applied first, then the identifier is restricted to a deliberately small
    ASCII grammar. This prevents zero-width/control characters, bidi marks,
    whitespace variants, and Unicode homoglyphs from creating visually
    confusable but distinct refusal identities.
    """
    if not isinstance(value, str) or not value:
        raise CanonicalizationError("effect_id must be a non-empty string")
    normalized = unicodedata.normalize("NFC", value)
    if not _EFFECT_ID_RE.fullmatch(normalized):
        raise CanonicalizationError("effect_id must match [A-Za-z0-9._:-]+ after NFC normalization")
    return normalized

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
