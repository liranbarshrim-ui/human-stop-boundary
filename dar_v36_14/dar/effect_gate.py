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
            if not self.k.verify_locked(c,req.principal,req.domain,req.action,req.effect_class,s):
                raise EffectDenied('invalid capability')
            key=f'{c.txid}:{req.effect_id}'
            if c.nonce in s.consumed or c.txid in s.consumed or key in s.consumed:
                raise EffectDenied('replay')
            from .store import Snapshot
            effects = set(s.effects)
            effects.add(key)
            ns=Snapshot(s.epoch,s.sequence+1,s.nonces,s.consumed|{c.nonce,c.txid,key},s.commits,s.state_payload,s.boot_id,tuple(sorted(effects)),s.pending_effects)
            self.k.store._write_atomic(ns)
        # The durable effect ledger gives registered effects a stable idempotency key.
        # It does NOT claim exactly-once semantics for arbitrary external side effects.
        return executor()

    def execute_recoverable(self, req, adapter, params, journal):
        """Execute through a recoverable adapter with a durable intent.

        The capability is authorized, consumed, and paired with a durable
        recoverable intent in the authenticated Store before the adapter is
        invoked. The intent records the effect identity, idempotency key,
        effect class, and parameter digest.

        The audit journal is a second durable record. PREPARED must be
        appended successfully before the external effect is executed; if that
        append fails, execution fails closed and the Store retains the intent
        for later reconciliation. A crash after PREPARED but before COMMITTED,
        or after COMMITTED before Store cleanup, is recoverable through the
        adapter's idempotency/status contract.

        Store intent and journal records are intentionally not a single
        cross-file atomic transaction. The Store is therefore the durable
        recovery source for an authorized-but-not-finalized intent, while the
        journal provides an independently authenticated audit trail.
        """
        if req.effect_class not in self.DECLARED or req.effect_class != req.action:
            raise EffectDenied('invalid effect class/action')
        import hashlib, json
        params_digest=hashlib.sha256(json.dumps(params,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        ikey=f'{req.capability.txid}:{req.effect_id}'
        intent={'key':f'{req.capability.txid}:{req.effect_id}','capability_txid':req.capability.txid,'effect_id':req.effect_id,'idempotency_key':ikey,'effect_class':req.effect_class,'params_digest':params_digest}
        with self.k.store.tx():
            s=self.k.store._read(); c=req.capability
            if not self.k.verify_locked(c,req.principal,req.domain,req.action,req.effect_class,s):
                raise EffectDenied('invalid capability')
            key=intent['key']
            if c.nonce in s.consumed or c.txid in s.consumed or key in s.consumed:
                raise EffectDenied('replay')
            pending=dict((x['key'],x) for x in s.pending_effects)
            if key in pending and pending[key] != intent:
                raise EffectDenied('conflicting durable intent')
            pending[key]=intent
            from .store import Snapshot
            ns=Snapshot(s.epoch,s.sequence,s.nonces,s.consumed|{c.nonce,c.txid,key},s.commits,s.state_payload,s.boot_id,tuple(sorted(set(s.effects)|{key})),tuple(pending.values()))
            self.k.store._write_atomic(ns)
        # The audit journal is part of the fail-closed execution boundary.
        # The Store already contains the recoverable intent, so a journal outage
        # must stop before the external effect rather than allowing an
        # un-audited effect to execute.
        journal.append({'status':'PREPARED',**intent})
        result=adapter.execute(ikey,params)
        # Never record COMMITTED merely because execute() returned. The adapter's
        # authoritative status must confirm the external effect is committed.
        status=adapter.status(ikey)
        from .effect_transaction import TxnStatus, AdapterContractError
        if status != TxnStatus.COMMITTED and status != 'COMMITTED':
            raise AdapterContractError(f'adapter did not confirm COMMITTED status: {status}')
        journal.append({'status':'COMMITTED',**intent})
        with self.k.store.tx():
            s=self.k.store._read()
            pending=tuple(x for x in s.pending_effects if x.get('key') != key)
            from .store import Snapshot
            self.k.store._write_atomic(Snapshot(s.epoch,s.sequence+1,s.nonces,s.consumed,s.commits,s.state_payload,s.boot_id,s.effects,pending))
        return result

    def reconcile_pending(self, adapter, journal, params_provider):
        """Reconcile Store intents left pending after a crash or journal failure.

        ``params_provider(intent)`` must return the original parameters. DAR
        verifies their digest before any adapter execution. Pending state is
        removed only after adapter status is COMMITTED and the journal contains
        a matching COMMITTED record.
        """
        from .effect_transaction import EffectTxn, recover, AdapterContractError, _params_digest
        from .store import Snapshot
        records = journal._validated_state()
        pending = tuple(self.k.store._read().pending_effects)
        for intent in pending:
            key = intent['key']
            existing = records.get(key)
            if existing is None:
                journal.append({'status': 'PREPARED', **intent})
                records = journal._validated_state()
                existing = records[key]
            for field in ('capability_txid','effect_id','idempotency_key','effect_class','params_digest'):
                if existing.get(field) != intent.get(field):
                    raise EffectDenied(f'pending intent does not match journal: {field}')
            params = params_provider(intent)
            if _params_digest(params) != intent['params_digest']:
                raise AdapterContractError('reconciliation params do not match durable intent')
            txn = EffectTxn(key, intent['idempotency_key'], intent['effect_class'], intent['params_digest'])
            recover(adapter, txn, params)
            records = journal._validated_state()
            if records.get(key, {}).get('status') != 'COMMITTED':
                journal.append({'status': 'COMMITTED', **intent})
                records = journal._validated_state()
            if records.get(key, {}).get('status') != 'COMMITTED':
                raise AdapterContractError('reconciliation did not establish COMMITTED journal state')
            with self.k.store.tx():
                s = self.k.store._read()
                still = tuple(x for x in s.pending_effects if x.get('key') != key)
                self.k.store._write_atomic(Snapshot(s.epoch, s.sequence + 1, s.nonces, s.consumed, s.commits, s.state_payload, s.boot_id, s.effects, still))
        return len(pending)
