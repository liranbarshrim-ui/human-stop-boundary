from dataclasses import dataclass
from enum import Enum
class TxState(str, Enum):
    PREPARED='PREPARED'; COMMITTED='COMMITTED'; ABORTED='ABORTED'
@dataclass(frozen=True)
class EffectIntent:
    effect_key: str
    effect_class: str
    idempotency_key: str
    params_digest: str
class RecoveryRequired(RuntimeError): pass
