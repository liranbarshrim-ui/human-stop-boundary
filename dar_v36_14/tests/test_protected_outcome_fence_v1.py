import tempfile
import unittest
from pathlib import Path
from dar import Kernel, Snapshot, Store, SystemState
from dar.effect_gate import EffectDenied, EffectGate, EffectRequest
from dar.effect_transaction import FencedEffectAdapter, TxnStatus, AdapterContractError, EffectTxn, protected_commit
from dar.refusal import RefusalAuthority

SECRET=b'x'*32

class FencedAdapter(FencedEffectAdapter):
    def __init__(self, epoch=0):
        self.fences={}; self.effects={}; self.default_epoch=epoch; self.execute_calls=0
    def current_fence(self, outcome_key): return self.fences.get(outcome_key,self.default_epoch)
    def advance_fence(self, outcome_key, epoch):
        current=self.current_fence(outcome_key)
        if epoch < current: raise ValueError('fence rollback')
        self.fences[outcome_key]=epoch
    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        if self.current_fence(outcome_key) != fence_epoch: raise RuntimeError('fence advanced')
        if idempotency_key in self.effects: return TxnStatus.COMMITTED
        self.effects[idempotency_key]=(outcome_key,dict(params)); return TxnStatus.COMMITTED
    def status(self, idempotency_key): return TxnStatus.COMMITTED if idempotency_key in self.effects else TxnStatus.UNKNOWN
    def execute(self, idempotency_key, params):
        self.execute_calls += 1; return self.commit(idempotency_key,'legacy',self.default_epoch,params)

class RacingFenceAdapter(FencedAdapter):
    """Adversarial model: the fence changes after DAR's advisory pre-check."""
    def __init__(self): super().__init__(1); self.raced=False
    def current_fence(self, outcome_key):
        value=super().current_fence(outcome_key)
        if not self.raced:
            self.raced=True; self.fences[outcome_key]=2
        return value

class Journal:
    def __init__(self): self.rows=[]
    def append(self,row): self.rows.append(dict(row))
    def _validated_state(self): return {r['key']:dict(r) for r in self.rows}

class ProtectedOutcomeFenceTests(unittest.TestCase):
    def make(self,d):
        store=Store(Path(d)/'state',SECRET)
        state=SystemState(0,{'human':{'root':frozenset({'WRITE','READ'})}}, {})
        store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),state.canonical(),'B'))
        return store,Kernel(store,SECRET,boot_id='B')
    def state(self,epoch): return SystemState(epoch,{'human':{'root':frozenset({'WRITE','READ'})}}, {})

    def test_outcome_refusal_blocks_a_new_effect_id_for_same_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); gate=EffectGate(kernel); adapter=FencedAdapter(); outcome='aabbcc'
            cap1=kernel.issue_protected('human','root','WRITE',self.state(1),nonce='n1',params={'amount':1},effect_id='000001',outcome_key=outcome); adapter.fences[outcome]=1
            refusal=RefusalAuthority(store,{'human':SECRET}).issue_protected('human','000001',cap1.txid,outcome,target_epoch=2); RefusalAuthority(store,{'human':SECRET}).commit_protected(refusal,adapter)
            cap2=kernel.issue_protected('human','root','WRITE',self.state(2),nonce='n2',params={'amount':1},effect_id='000002',outcome_key=outcome); req=EffectRequest(cap2,'human','root','WRITE','000002','WRITE',outcome)
            with self.assertRaises(EffectDenied): gate.execute_protected(req,adapter,{'amount':1},Journal())
            self.assertEqual(adapter.effects,{})

    def test_refusal_fence_wins_after_crash_before_journal(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); adapter=FencedAdapter(); outcome='deadbeef'; adapter.fences[outcome]=1
            cap=kernel.issue_protected('human','root','WRITE',self.state(1),nonce='n1',params={'amount':7},effect_id='000003',outcome_key=outcome)
            refusal=RefusalAuthority(store,{'human':SECRET}).issue_protected('human','000003',cap.txid,outcome,target_epoch=2); RefusalAuthority(store,{'human':SECRET}).commit_protected(refusal,adapter)
            with self.assertRaises(RuntimeError): adapter.commit('crashed-key',outcome,1,{'amount':7})
            self.assertNotIn('crashed-key',adapter.effects)

    def test_unfenced_adapter_cannot_claim_strong_protected_outcome(self):
        class UnsafeAdapter:
            def status(self,k): return TxnStatus.UNKNOWN
            def execute(self,k,p): return None
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); gate=EffectGate(kernel); outcome='cafebabe'; adapter=UnsafeAdapter()
            cap=kernel.issue_protected('human','root','WRITE',self.state(1),nonce='n1',params={'x':1},effect_id='000004',outcome_key=outcome); req=EffectRequest(cap,'human','root','WRITE','000004','WRITE',outcome)
            with self.assertRaises(EffectDenied): gate.execute_protected(req,adapter,{'x':1},Journal())

    def test_protected_reconcile_never_calls_unfenced_execute(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); gate=EffectGate(kernel); adapter=FencedAdapter(); outcome='facefeed'; adapter.fences[outcome]=1
            intent={'key':'tx:000005','capability_txid':'tx','effect_id':'000005','outcome_key':outcome,'idempotency_key':'tx:000005','effect_class':'WRITE','params_digest':kernel._params_digest({'x':5}),'epoch':0}
            s=store._read(); store._write_atomic(Snapshot(s.epoch,s.sequence+1,s.nonces,s.consumed,s.commits,s.state_payload,s.boot_id,s.effects,(intent,))); journal=Journal()
            self.assertEqual(gate.reconcile_pending(adapter,journal,lambda _intent:{'x':5}),1); self.assertEqual(adapter.execute_calls,0); self.assertEqual(adapter.effects['tx:000005'][0],outcome)

    def test_protected_reconcile_refuses_after_external_fence_advance(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); gate=EffectGate(kernel); adapter=FencedAdapter(); outcome='badc0de'; adapter.fences[outcome]=1
            intent={'key':'tx:000006','capability_txid':'tx','effect_id':'000006','outcome_key':outcome,'idempotency_key':'tx:000006','effect_class':'WRITE','params_digest':kernel._params_digest({'x':6}),'epoch':0}
            s=store._read(); store._write_atomic(Snapshot(s.epoch,s.sequence+1,s.nonces,s.consumed,s.commits,s.state_payload,s.boot_id,s.effects,(intent,)))
            refusal=RefusalAuthority(store,{'human':SECRET}).issue_protected('human','000006','tx',outcome,target_epoch=2); RefusalAuthority(store,{'human':SECRET}).commit_protected(refusal,adapter); journal=Journal()
            self.assertEqual(gate.reconcile_pending(adapter,journal,lambda _intent:{'x':6}),1); self.assertEqual(adapter.execute_calls,0); self.assertNotIn('tx:000006',adapter.effects); self.assertEqual(journal._validated_state()['tx:000006']['status'],'REFUSED')

    def test_adversarial_race_after_advisory_fence_check_cannot_commit(self):
        adapter=RacingFenceAdapter(); txn=EffectTxn('k','k','WRITE','x','aabbcc',1)
        with self.assertRaises(AdapterContractError): protected_commit(adapter,txn,{'x':1})
        self.assertEqual(adapter.effects,{})

if __name__=='__main__': unittest.main()
