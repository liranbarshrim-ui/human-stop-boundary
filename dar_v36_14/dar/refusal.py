from dataclasses import dataclass
import hashlib
import hmac
import time
import uuid
from .canonical import canonical_effect_id, canonical_outcome_key

@dataclass(frozen=True)
class RefusalIntent:
    refusal_id: str
    principal: str
    effect_id: str
    capability_txid: str
    target_epoch: int
    issued_at: int
    mac: str
    outcome_key: str = ''

class RefusalAuthority:
    """Authenticated refusal authority with outcome-level fencing."""
    def __init__(self, store, principal_credentials):
        self.store = store; self.credentials = dict(principal_credentials)

    @staticmethod
    def _payload(refusal_id, principal, effect_id, capability_txid, target_epoch, issued_at, outcome_key=''):
        return '|'.join(map(str, (refusal_id, principal, effect_id, capability_txid, target_epoch, issued_at, outcome_key))).encode()

    def _mac(self, credential, *fields): return hmac.new(credential, self._payload(*fields), hashlib.sha256).hexdigest()

    def issue(self, principal, effect_id, capability_txid, target_epoch=None, refusal_id=None, issued_at=None, outcome_key=None):
        if principal not in self.credentials: raise PermissionError('principal is not authorized to refuse effects')
        effect_id = canonical_effect_id(effect_id); outcome_key = canonical_outcome_key(outcome_key) if outcome_key is not None else ''
        refusal_id = refusal_id or str(uuid.uuid4()); issued_at = int(time.time()) if issued_at is None else int(issued_at)
        with self.store.tx():
            s=self.store._read(); epoch=s.epoch if target_epoch is None else int(target_epoch)
            if epoch <= s.epoch: epoch=s.epoch+1
            mac=self._mac(self.credentials[principal],refusal_id,principal,effect_id,capability_txid,epoch,issued_at,outcome_key)
            return RefusalIntent(refusal_id,principal,effect_id,capability_txid,epoch,issued_at,mac,outcome_key)

    def issue_protected(self, principal, effect_id, capability_txid, outcome_key, target_epoch=None, refusal_id=None, issued_at=None):
        if outcome_key is None: raise ValueError('protected refusal requires an explicit outcome_key')
        return self.issue(principal,effect_id,capability_txid,target_epoch,refusal_id,issued_at,outcome_key)

    def verify(self, refusal):
        credential=self.credentials.get(refusal.principal)
        if credential is None: return False
        try:
            effect_id=canonical_effect_id(refusal.effect_id); outcome_key=canonical_outcome_key(refusal.outcome_key) if refusal.outcome_key else ''
        except Exception: return False
        if effect_id!=refusal.effect_id or outcome_key!=getattr(refusal,'outcome_key',''): return False
        expected=self._mac(credential,refusal.refusal_id,refusal.principal,effect_id,refusal.capability_txid,refusal.target_epoch,refusal.issued_at,outcome_key)
        return hmac.compare_digest(expected,refusal.mac)

    def _append_refusal_locked(self, s, refusal):
        from .store import Snapshot
        payload=dict(s.state_payload); payload['epoch']=refusal.target_epoch
        refusals=list(payload.get('refusals',[])); refusals.append({'refusal_id':refusal.refusal_id,'principal':refusal.principal,'effect_id':refusal.effect_id,'capability_txid':refusal.capability_txid,'target_epoch':refusal.target_epoch,'issued_at':refusal.issued_at,'mac':refusal.mac,'outcome_key':getattr(refusal,'outcome_key','')}); payload['refusals']=refusals
        return Snapshot(refusal.target_epoch,s.sequence+1,s.nonces,s.consumed,s.commits,payload,s.boot_id,s.effects,s.pending_effects)

    def commit(self, refusal):
        if not self.verify(refusal): raise PermissionError('invalid refusal authentication')
        from .store import Snapshot
        with self.store.tx():
            s=self.store._read()
            if refusal.target_epoch<=s.epoch: raise ValueError('refusal target epoch is not newer than current epoch')
            self.store._write_atomic(self._append_refusal_locked(s,refusal)); return refusal

    def commit_protected(self, refusal, adapter):
        """Advance the external fence before publishing the durable refusal.

        Safety ordering is deliberate: once the external fence is advanced,
        no later protected commit for this outcome can succeed. A crash after
        the fence advance may reduce availability, but cannot permit a stale
        protected commit. The adapter must make fence advancement authoritative
        at the same external commit point used by FencedEffectAdapter.commit.
        """
        if not self.verify(refusal) or not refusal.outcome_key:
            raise PermissionError('invalid or unbound protected refusal')
        with self.store.tx():
            s=self.store._read()
            if refusal.target_epoch<=s.epoch: raise ValueError('refusal target epoch is not newer than current epoch')
            outcome_key=canonical_outcome_key(refusal.outcome_key)
            current=int(adapter.current_fence(outcome_key))
            if current>int(refusal.target_epoch): raise ValueError('external refusal fence already advanced')
            if current==int(refusal.target_epoch): raise ValueError('external refusal fence already committed')
            adapter.advance_fence(outcome_key,int(refusal.target_epoch))
            if int(adapter.current_fence(outcome_key))!=int(refusal.target_epoch): raise RuntimeError('adapter did not durably advance refusal fence')
            self.store._write_atomic(self._append_refusal_locked(s,refusal)); return refusal
