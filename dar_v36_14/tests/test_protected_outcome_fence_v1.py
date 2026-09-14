import tempfile
import unittest
from pathlib import Path
from dar import Kernel, Snapshot, Store, SystemState
from dar.effect_gate import EffectDenied, EffectGate, EffectRequest
from dar.effect_transaction import FencedEffectAdapter, TxnStatus
from dar.refusal import RefusalAuthority

SECRET=b'x'*32

class FencedAdapter(FencedEffectAdapter):
    def __init__(self, epoch=0):
        self.fences={}
        self.effects={}
        self.default_epoch=epoch
    def current_fence(self, outcome_key):
        return self.fences.get(outcome_key,self.default_epoch)
    def advance_fence(self, outcome_key, epoch):
        current=self.current_fence(outcome_key)
        if epoch < current: raise ValueError('fence rollback')
        self.fences[outcome_key]=epoch
    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        if self.current_fence(outcome_key) != fence_epoch:
            raise RuntimeError('fence advanced')
        if idempotency_key in self.effects: return TxnStatus.COMMITTED
        self.effects[idempotency_key]=(outcome_key,dict(params))
        return TxnStatus.COMMITTED
    def status(self, idempotency_key):
        return TxnStatus.COMMITTED if idempotency_key in self.effects else TxnStatus.UNKNOWN
    def execute(self, idempotency_key, params):
        return self.commit(idempotency_key, 'legacy', self.default_epoch, params)

class Journal:
    def __init__(self): self.rows=[]
    def append(self,row): self.rows.append(dict(row))

class ProtectedOutcomeFenceTests(unittest.TestCase):
    def make(self,d):
        store=Store(Path(d)/'state',SECRET)
        state=SystemState(0,{'human':{'root':frozenset({'WRITE','READ'})}}, {})
        store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),state.canonical(),'B'))
        return store,Kernel(store,SECRET,boot_id='B')

    def state(self,epoch):
        return SystemState(epoch,{'human':{'root':frozenset({'WRITE','READ'})}}, {})

    def test_outcome_refusal_blocks_a_new_effect_id_for_same_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); gate=EffectGate(kernel); adapter=FencedAdapter()
            outcome='aabbcc'; cap1=kernel.issue_protected('human','root','WRITE',self.state(1),nonce='n1',params={'amount':1},effect_id='000001',outcome_key=outcome)
            adapter.fences[outcome]=1
            refusal=RefusalAuthority(store,{'human':SECRET}).issue_protected('human','000001',cap1.txid,outcome,target_epoch=2)
            RefusalAuthority(store,{'human':SECRET}).commit_protected(refusal,adapter)
            cap2=kernel.issue_protected('human','root','WRITE',self.state(2),nonce='n2',params={'amount':1},effect_id='000002',outcome_key=outcome)
            req=EffectRequest(cap2,'human','root','WRITE','000002','WRITE',outcome)
            with self.assertRaises(EffectDenied): gate.execute_protected(req,adapter,{'amount':1},Journal())
            self.assertEqual(adapter.effects,{})

    def test_refusal_fence_wins_after_crash_before_journal(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); adapter=FencedAdapter(); outcome='deadbeef'; adapter.fences[outcome]=1
            cap=kernel.issue_protected('human','root','WRITE',self.state(1),nonce='n1',params={'amount':7},effect_id='000003',outcome_key=outcome)
            refusal=RefusalAuthority(store,{'human':SECRET}).issue_protected('human','000003',cap.txid,outcome,target_epoch=2)
            RefusalAuthority(store,{'human':SECRET}).commit_protected(refusal,adapter)
            with self.assertRaises(RuntimeError): adapter.commit('crashed-key',outcome,1,{'amount':7})
            self.assertNotIn('crashed-key',adapter.effects)

    def test_unfenced_adapter_cannot_claim_strong_protected_outcome(self):
        class UnsafeAdapter:
            def status(self,k): return TxnStatus.UNKNOWN
            def execute(self,k,p): return None
        with tempfile.TemporaryDirectory() as d:
            store,kernel=self.make(d); gate=EffectGate(kernel); outcome='cafebabe'; adapter=UnsafeAdapter()
            cap=kernel.issue_protected('human','root','WRITE',self.state(1),nonce='n1',params={'x':1},effect_id='000004',outcome_key=outcome)
            req=EffectRequest(cap,'human','root','WRITE','000004','WRITE',outcome)
            with self.assertRaises(EffectDenied): gate.execute_protected(req,adapter,{'x':1},Journal())

if __name__=='__main__': unittest.main()
