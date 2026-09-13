from dataclasses import dataclass
class EffectDenied(Exception): pass
@dataclass(frozen=True)
class EffectRequest:
    capability:object; principal:str; domain:str; action:str; effect_id:str; effect_class:str
class EffectGate:
    DECLARED={'READ','WRITE','NETWORK','PROCESS'}
    def __init__(self,kernel): self.k=kernel
    def execute(self,req,executor):
        if req.effect_class not in self.DECLARED: raise EffectDenied('undeclared effect class')
        if req.effect_class != req.action: raise EffectDenied('action/effect-class mismatch')
        with self.k.store.tx():
            s=self.k.store._read(); c=req.capability
            if not self.k.verify_locked(c,req.principal,req.domain,req.action,req.effect_class,s): raise EffectDenied('invalid capability')
            key=f'{c.txid}:{req.effect_id}'
            if c.nonce in s.consumed or c.txid in s.consumed or key in s.consumed: raise EffectDenied('replay')
            from .store import Snapshot
            effects=set(s.effects); effects.add(key)
            ns=Snapshot(s.epoch,s.sequence,s.nonces,s.consumed|{c.nonce,c.txid,key},s.commits,s.state_payload,s.boot_id,tuple(sorted(effects)))
            self.k.store._write_atomic(ns)
        return executor()
    def execute_recoverable(self,req,adapter,params,journal):
        """Execute a recoverable effect with durable intent before adapter execution.

        The capability is authorized, consumed, and paired with a durable
        recoverable intent in the authenticated Store before the adapter is
        invoked. The intent records the effect identity, idempotency key,
        effect class, and parameter digest.

        The audit journal is a second durable record. PREPARED must be appended
        successfully before the external effect is executed; if that append
        fails, execution fails closed and the Store retains the intent for
        reconciliation. A crash after PREPARED but before COMMITTED is
        recoverable through the adapter's idempotency/status contract.

        Store intent and journal records are intentionally not a single
        cross-file atomic transaction. The Store is therefore the durable
        recovery source for an authorized-but-not-finalized intent, while the
        journal provides an independently authenticated audit trail.
        """
        if req.effect_class not in self.DECLARED or req.effect_class != req.action: raise EffectDenied('invalid effect class/action')
        import hashlib,json
        params_digest=hashlib.sha256(json.dumps(params,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        ikey=f'{req.capability.txid}:{req.effect_id}'
        intent={'key':ikey,'capability_txid':req.capability.txid,'effect_id':req.effect_id,'idempotency_key':ikey,'effect_class':req.effect_class,'params_digest':params_digest}
        with self.k.store.tx():
            s=self.k.store._read(); c=req.capability
            if not self.k.verify_locked(c,req.principal,req.domain,req.action,req.effect_class,s): raise EffectDenied('invalid capability')
            if c.nonce in s.consumed or c.txid in s.consumed or ikey in s.consumed: raise EffectDenied('replay')
            pending=dict((x['key'],x) for x in s.pending_effects)
            if ikey in pending and pending[ikey] != intent: raise EffectDenied('conflicting durable intent')
            pending[ikey]=intent
            from .store import Snapshot
            ns=Snapshot(s.epoch,s.sequence,s.nonces,s.consumed|{c.nonce,c.txid,ikey},s.commits,s.state_payload,s.boot_id,tuple(sorted(set(s.effects)|{ikey})),tuple(pending.values()))
            self.k.store._write_atomic(ns)
        # Fail closed if the audit journal cannot record the durable intent.
        journal.append({'status':'PREPARED',**intent})
        result=adapter.execute(ikey,params)
        status=adapter.status(ikey)
        from .effect_transaction import TxnStatus, AdapterContractError
        if status != TxnStatus.COMMITTED and status != 'COMMITTED':
            raise AdapterContractError(f'adapter did not confirm COMMITTED status: {status}')
        journal.append({'status':'COMMITTED',**intent})
        with self.k.store.tx():
            s=self.k.store._read(); pending=tuple(x for x in s.pending_effects if x.get('key') != ikey)
            from .store import Snapshot
            self.k.store._write_atomic(Snapshot(s.epoch,s.sequence,s.nonces,s.consumed,s.commits,s.state_payload,s.boot_id,s.effects,pending))
        return result
