from dataclasses import dataclass
import hashlib
import hmac
import json
import time
import uuid
from .canonical import canonical_effect_id


@dataclass(frozen=True)
class RefusalIntent:
    refusal_id: str
    principal: str
    effect_id: str
    capability_txid: str
    target_epoch: int
    issued_at: int
    mac: str


class RefusalAuthority:
    """Minimal authenticated refusal authority.

    The refusal credential is deliberately separate from the Kernel capability
    secret. A deployment must provision one credential per authorized principal
    and protect the credential outside the effect-gate process.
    """

    def __init__(self, store, principal_credentials):
        self.store = store
        self.credentials = dict(principal_credentials)

    @staticmethod
    def _payload(refusal_id, principal, effect_id, capability_txid, target_epoch, issued_at):
        return '|'.join(map(str, (refusal_id, principal, effect_id, capability_txid, target_epoch, issued_at))).encode()

    def _mac(self, credential, *fields):
        return hmac.new(credential, self._payload(*fields), hashlib.sha256).hexdigest()

    def issue(self, principal, effect_id, capability_txid, target_epoch=None, refusal_id=None, issued_at=None):
        if principal not in self.credentials:
            raise PermissionError('principal is not authorized to refuse effects')
        effect_id = canonical_effect_id(effect_id)
        refusal_id = refusal_id or str(uuid.uuid4())
        issued_at = int(time.time()) if issued_at is None else int(issued_at)
        with self.store.tx():
            s = self.store._read()
            epoch = s.epoch if target_epoch is None else int(target_epoch)
            if epoch <= s.epoch:
                epoch = s.epoch + 1
            mac = self._mac(self.credentials[principal], refusal_id, principal, effect_id, capability_txid, epoch, issued_at)
            return RefusalIntent(refusal_id, principal, effect_id, capability_txid, epoch, issued_at, mac)

    def verify(self, refusal):
        credential = self.credentials.get(refusal.principal)
        if credential is None:
            return False
        try:
            effect_id = canonical_effect_id(refusal.effect_id)
        except Exception:
            return False
        if effect_id != refusal.effect_id:
            return False
        expected = self._mac(credential, refusal.refusal_id, refusal.principal, effect_id, refusal.capability_txid, refusal.target_epoch, refusal.issued_at)
        return hmac.compare_digest(expected, refusal.mac)

    def commit(self, refusal):
        if not self.verify(refusal):
            raise PermissionError('invalid refusal authentication')
        from .store import Snapshot
        with self.store.tx():
            s = self.store._read()
            if refusal.target_epoch <= s.epoch:
                raise ValueError('refusal target epoch is not newer than current epoch')
            payload = dict(s.state_payload)
            payload['epoch'] = refusal.target_epoch
            refusals = list(payload.get('refusals', []))
            refusals.append({'refusal_id': refusal.refusal_id, 'principal': refusal.principal, 'effect_id': refusal.effect_id, 'capability_txid': refusal.capability_txid, 'target_epoch': refusal.target_epoch, 'issued_at': refusal.issued_at, 'mac': refusal.mac})
            payload['refusals'] = refusals
            self.store._write_atomic(Snapshot(refusal.target_epoch, s.sequence + 1, s.nonces, s.consumed, s.commits, payload, s.boot_id, s.effects, s.pending_effects))
            return refusal
