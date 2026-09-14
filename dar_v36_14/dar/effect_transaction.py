"""Crash-aware effect transaction contracts.

The ordinary RecoverableEffectAdapter contract is NOT sufficient to prove an
external outcome did not occur after a DAR refusal. Strong protected-outcome
claims require a fenced adapter whose commit operation atomically checks the
current monotonic fence in the same authority that makes the external effect.
"""
from dataclasses import dataclass
from enum import Enum
from .canonical import canonical_digest, canonical_outcome_key

class TxnStatus(str, Enum):
    UNKNOWN='UNKNOWN'; PREPARED='PREPARED'; COMMITTED='COMMITTED'; FAILED='FAILED'; REFUSED='REFUSED'

@dataclass(frozen=True)
class EffectTxn:
    effect_key: str
    idempotency_key: str
    effect_class: str
    params_digest: str
    outcome_key: str = ''
    fence_epoch: int = 0

class AdapterContractError(RuntimeError): pass

class RecoverableEffectAdapter:
    def status(self, idempotency_key): raise NotImplementedError
    def execute(self, idempotency_key, params): raise NotImplementedError

class FencedEffectAdapter(RecoverableEffectAdapter):
    """Required boundary for the strong `NO => no protected_commit` claim.

    `commit` MUST atomically enforce: fence_epoch is still current for
    outcome_key, and no protected external effect is made if the fence has
    already advanced. The adapter's status must durably reflect the same
    external transaction and be authoritative for recovery.
    """
    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        raise NotImplementedError

    def current_fence(self, outcome_key):
        raise NotImplementedError

def _params_digest(params): return canonical_digest(params)

def recover(adapter, txn, params):
    if _params_digest(params) != txn.params_digest: raise AdapterContractError('recovery params do not match durable intent')
    st = adapter.status(txn.idempotency_key)
    if st == TxnStatus.COMMITTED: return st
    if st not in (TxnStatus.UNKNOWN, TxnStatus.PREPARED): raise AdapterContractError(f'unexpected adapter status: {st}')
    adapter.execute(txn.idempotency_key, params)
    final = adapter.status(txn.idempotency_key)
    if final != TxnStatus.COMMITTED and final != 'COMMITTED': raise AdapterContractError(f'adapter did not confirm COMMITTED status after recovery: {final}')
    return final

def protected_commit(adapter, txn, params):
    """Perform an externally fenced commit; refusal wins once its fence is advanced."""
    if not isinstance(adapter, FencedEffectAdapter):
        raise AdapterContractError('strong protected outcome requires FencedEffectAdapter')
    if _params_digest(params) != txn.params_digest: raise AdapterContractError('commit params do not match durable intent')
    outcome_key = canonical_outcome_key(txn.outcome_key)
    fence = adapter.current_fence(outcome_key)
    if int(fence) != int(txn.fence_epoch):
        raise AdapterContractError('protected outcome fence is no longer current')
    try:
        return adapter.commit(txn.idempotency_key, outcome_key, txn.fence_epoch, params)
    except Exception as exc:
        raise AdapterContractError(f'fenced protected commit rejected: {exc}') from exc
