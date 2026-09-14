from dataclasses import dataclass
from .canonical import canonical_effect_id, canonical_outcome_key
class EffectDenied(Exception): pass
@dataclass(frozen=True)
class EffectRequest:
    capability:object; principal:str; domain:str; action:str; effect_id:str; effect_class:str; outcome_key:str=''
class EffectGate:
    DECLARED={'READ','WRITE','NETWORK','PROCESS'}
    def __init__(self,kernel): self.k=kernel
    def _is_refused(self,state,effect_id,outcome_key=''):
        try:
            effect_id=canonical_effect_id(effect_id); outcome_key=canonical_outcome_key(outcome_key) if outcome_key else ''
        except Exception: return True
        return any(r.get('effect_id')==effect_id or (outcome_key and r.get('outcome_key')==outcome_key) for r in state.state_payload.get('refusals',[]))
    def _validate_common(self,req,params=None,require_outcome=False):
        if req.effect_class not in self.DECLARED: raise EffectDenied('undeclared effect class')
        if req.effect_class!=req.action: raise EffectDenied('action/effect-class mismatch')
        try: req_effect_id=canonical_effect_id(req.effect_id)
        except Exception: raise EffectDenied('invalid effect identity')
        cap_effect_id=getattr(req.capability,'effect_id','')
        if not cap_effect_id or req_effect_id!=cap_effect_id: raise EffectDenied('effect identity mismatch')
        cap_outcome=getattr(req.capability,'outcome_key','')
        if require_outcome:
            if not cap_outcome or not req.outcome_key: raise EffectDenied('protected outcome identity required')
            try:
                if canonical_outcome_key(cap_outcome)!=cap_outcome or canonical_outcome_key(req.outcome_key)!=req.outcome_key: raise EffectDenied('invalid outcome identity')
            except Exception: raise EffectDenied('invalid outcome identity')
            if req.outcome_key!=cap_outcome: raise EffectDenied('outcome identity mismatch')
        if params is not None:
            expected=self.k._params_digest(params)
            if expected!=getattr(req.capability,'params_digest',''): raise EffectDenied('parameter substitution')
        return req_effect_id,cap_outcome
    def execute(self,req,executor,params=None):
        effect_id,_=self._validate_common(req,params)
        with self.k.store.tx():
            s=self.k.store._read(); c=req.capability
            if self._is_refused(s,effect_id): raise EffectDenied('effect refused')
            if not self.k.verify_locked(c,req.principal,req.domain,req.action,req.effect_class,s): raise EffectDenied('invalid capability')
            key=f'{c.txid}:{effect_id}'
            if c.nonce in s.consumed or c.txid in s.consumed or key in s.consumed: raise EffectDenied('replay')
            from .store import Snapshot
            effects=set(s.effects); effects.add(key)
            self.k.store._write_atomic(Snapshot(s.epoch,s.sequence+1,s.nonces,s.consumed|{c.nonce,c.txid,key},s.commits,s.state_payload,s.boot_id,tuple(sorted(effects)),s.pending_effects)); return executor()
    def execute_protected(self,req,adapter,params,journal):
        effect_id,outcome_key=self._validate_common(req,params,require_outcome=True)
        from .effect_transaction import EffectTxn, protected_commit, AdapterContractError
        params_digest=self.k._params_digest(params); c=req.capability; key=f'{c.txid}:{effect_id}'
        with self.k.store.tx():
            s=self.k.store._read()
            if self._is_refused(s,effect_id,outcome_key): raise EffectDenied('protected outcome refused')
            if not self.k.verify_locked(c,req.principal,req.domain,req.action,req.effect_class,s): raise EffectDenied('invalid capability')
            if c.nonce in s.consumed or c.txid in s.consumed or key in s.consumed: raise EffectDenied('replay')
            from .store import Snapshot
            intent={'key':key,'capability_txid':c.txid,'effect_id':effect_id,'outcome_key':outcome_key,'idempotency_key':key,'effect_class':req.effect_class,'params_digest':params_digest,'epoch':s.epoch}
            self.k.store._write_atomic(Snapshot(s.epoch,s.sequence+1,s.nonces,s.consumed|{c.nonce,c.txid,key},s.commits,s.state_payload,s.boot_id,tuple(sorted(set(s.effects)|{key})),s.pending_effects+(intent,)))
            journal.append({'status':'PREPARED',**intent})
            txn=EffectTxn(key,key,req.effect_class,params_digest,outcome_key,s.epoch)
            try: result=protected_commit(adapter,txn,params)
            except AdapterContractError as exc: raise EffectDenied(str(exc)) from exc
            journal.append({'status':'COMMITTED',**intent})
            s2=self.k.store._read(); pending=tuple(x for x in s2.pending_effects if x.get('key')!=key)
            self.k.store._write_atomic(Snapshot(s2.epoch,s2.sequence+1,s2.nonces,s2.consumed,s2.commits,s2.state_payload,s2.boot_id,s2.effects,pending)); return result
    def execute_recoverable(self,req,adapter,params,journal):
        effect_id,_=self._validate_common(req,params)
        params_digest=self.k._params_digest(params); ikey=f'{req.capability.txid}:{effect_id}'
        with self.k.store.tx():
            s=self.k.store._read(); c=req.capability
            if self._is_refused(s,effect_id): raise EffectDenied('effect refused')
            if not self.k.verify_locked(c,req.principal,req.domain,req.action,req.effect_class,s): raise EffectDenied('invalid capability')
            key=ikey
            if c.nonce in s.consumed or c.txid in s.consumed or key in s.consumed: raise EffectDenied('replay')
            pending=dict((x['key'],x) for x in s.pending_effects); intent={'key':ikey,'capability_txid':c.txid,'effect_id':effect_id,'idempotency_key':ikey,'effect_class':req.effect_class,'params_digest':params_digest,'epoch':s.epoch}
            if key in pending and pending[key]!=intent: raise EffectDenied('conflicting durable intent')
            from .store import Snapshot
            ns=Snapshot(s.epoch,s.sequence+1,s.nonces,s.consumed|{c.nonce,c.txid,key},s.commits,s.state_payload,s.boot_id,tuple(sorted(set(s.effects)|{key})),tuple(pending.values())+((intent,) if key not in pending else ()))
            self.k.store._write_atomic(ns); journal.append({'status':'PREPARED',**intent})
            result=adapter.execute(ikey,params); status=adapter.status(ikey)
            from .effect_transaction import TxnStatus,AdapterContractError
            if status!=TxnStatus.COMMITTED and status!='COMMITTED': raise AdapterContractError(f'adapter did not confirm COMMITTED status: {status}')
            journal.append({'status':'COMMITTED',**intent}); s2=self.k.store._read(); pending2=tuple(x for x in s2.pending_effects if x.get('key')!=key)
            self.k.store._write_atomic(Snapshot(s2.epoch,s2.sequence+1,s2.nonces,s2.consumed,s2.commits,s2.state_payload,s2.boot_id,s2.effects,pending2)); return result
    def reconcile_pending(self,adapter,journal,params_provider):
        from .effect_transaction import EffectTxn,recover,protected_commit,AdapterContractError,_params_digest
        from .store import Snapshot
        with self.k.store.tx():
            records=journal._validated_state(); pending=tuple(self.k.store._read().pending_effects)
            for intent in pending:
                key=intent['key']; existing=records.get(key)
                if existing is None: journal.append({'status':'PREPARED',**intent}); records=journal._validated_state(); existing=records[key]
                for field in ('capability_txid','effect_id','idempotency_key','effect_class','params_digest'):
                    if existing.get(field)!=intent.get(field): raise EffectDenied(f'pending intent does not match journal: {field}')
                current=self.k.store._read(); outcome_key=intent.get('outcome_key','')
                if outcome_key:
                    try: outcome_key=canonical_outcome_key(outcome_key)
                    except Exception as exc: raise EffectDenied('protected pending intent has invalid outcome identity') from exc
                if self._is_refused(current,intent['effect_id'],outcome_key) or 'epoch' not in intent or int(intent['epoch'])!=current.epoch:
                    journal.append({'status':'REFUSED','reason':'effect refused or epoch advanced after pending intent',**intent}); still=tuple(x for x in current.pending_effects if x.get('key')!=key); self.k.store._write_atomic(Snapshot(current.epoch,current.sequence+1,current.nonces,current.consumed,current.commits,current.state_payload,current.boot_id,current.effects,still)); continue
                params=params_provider(intent)
                if _params_digest(params)!=intent['params_digest']: raise AdapterContractError('reconciliation params do not match durable intent')
                txn=EffectTxn(key,intent['idempotency_key'],intent['effect_class'],intent['params_digest'],outcome_key,int(intent['epoch']))
                if outcome_key:
                    # Protected pending intents may ONLY recover through the fenced commit path.
                    # Never route them through recover()/adapter.execute(), which is outside the strong claim.
                    try: protected_commit(adapter,txn,params)
                    except AdapterContractError as exc: raise EffectDenied(str(exc)) from exc
                else:
                    recover(adapter,txn,params)
                records=journal._validated_state()
                if records.get(key,{}).get('status')!='COMMITTED': journal.append({'status':'COMMITTED',**intent}); records=journal._validated_state()
                if records.get(key,{}).get('status')!='COMMITTED': raise AdapterContractError('reconciliation did not establish COMMITTED journal state')
                current=self.k.store._read()
                if self._is_refused(current,intent['effect_id'],outcome_key) or int(intent['epoch'])!=current.epoch: raise EffectDenied('refusal occurred before pending commit finalization')
                still=tuple(x for x in current.pending_effects if x.get('key')!=key); self.k.store._write_atomic(Snapshot(current.epoch,current.sequence+1,current.nonces,current.consumed,current.commits,current.state_payload,current.boot_id,current.effects,still))
            return len(pending)
