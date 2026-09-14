"""Crash-aware effect transaction contracts.

The ordinary RecoverableEffectAdapter contract is NOT sufficient to prove an
external outcome did not occur after a DAR refusal. Strong protected-outcome
claims require a fenced adapter whose commit operation atomically checks the
current monotonic fence and the authoritative terminal refusal state in the
same authority that makes the external effect.
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
    """Required boundary for the strong protected-outcome claim.

    The external authority must durably record terminal refusal state for an
    outcome. `commit` must atomically reject when that outcome is refused,
    regardless of numeric fence equality, and must atomically enforce that the
    supplied fence is still current before making the protected effect.
    """
    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        raise NotImplementedError

    def current_fence(self, outcome_key):
        raise NotImplementedError

    def refuse_outcome(self, outcome_key, fence_epoch, refusal_id):
        """Atomically install the terminal external refusal marker."""
        raise NotImplementedError

    def is_refused(self, outcome_key):
        """Return authoritative terminal refusal state for an outcome."""
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
    """Perform an externally fenced commit; terminal refusal wins atomically."""
    if not isinstance(adapter, FencedEffectAdapter):
        raise AdapterContractError('strong protected outcome requires FencedEffectAdapter')
    if _params_digest(params) != txn.params_digest: raise AdapterContractError('commit params do not match durable intent')
    outcome_key = canonical_outcome_key(txn.outcome_key)
    if adapter.is_refused(outcome_key):
        raise AdapterContractError('protected outcome is terminally refused')
    fence = adapter.current_fence(outcome_key)
    if int(fence) != int(txn.fence_epoch):
        raise AdapterContractError('protected outcome fence is no longer current')
    try:
        return adapter.commit(txn.idempotency_key, outcome_key, txn.fence_epoch, params)
    except Exception as exc:
        raise AdapterContractError(f'fenced protected commit rejected: {exc}') from exc
