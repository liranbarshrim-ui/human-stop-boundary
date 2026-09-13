"""Crash-aware effect transaction contract."""
from dataclasses import dataclass
from enum import Enum
import hashlib
import json

class TxnStatus(str, Enum):
    UNKNOWN='UNKNOWN'; PREPARED='PREPARED'; COMMITTED='COMMITTED'; FAILED='FAILED'

@dataclass(frozen=True)
class EffectTxn:
    effect_key: str
    idempotency_key: str
    effect_class: str
    params_digest: str

class AdapterContractError(RuntimeError): pass

class RecoverableEffectAdapter:
    def status(self, idempotency_key): raise NotImplementedError
    def execute(self, idempotency_key, params): raise NotImplementedError

def _params_digest(params):
    return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def recover(adapter, txn, params):
    if _params_digest(params) != txn.params_digest:
        raise AdapterContractError('recovery params do not match durable intent')
    st = adapter.status(txn.idempotency_key)
    if st == TxnStatus.COMMITTED: return st
    if st not in (TxnStatus.UNKNOWN, TxnStatus.PREPARED):
        raise AdapterContractError(f'unexpected adapter status: {st}')
    adapter.execute(txn.idempotency_key, params)
    final = adapter.status(txn.idempotency_key)
    if final != TxnStatus.COMMITTED and final != 'COMMITTED':
        raise AdapterContractError(f'adapter did not confirm COMMITTED status after recovery: {final}')
    return final
