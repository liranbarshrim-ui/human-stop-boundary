import hashlib,json,tempfile,unittest
from pathlib import Path
from dar import GovernanceRule,Kernel,Snapshot,Store,SystemState
from dar.effect_journal import EffectJournal
from dar.effect_transaction import AdapterContractError,EffectTxn,TxnStatus,recover,_params_digest
from dar.policy import validate_transition

class Anchor:
    def __init__(self): self.v=0
    def floor(self): return self.v
    def advance_to(self,n):
        if n<self.v: raise ValueError('anchor rollback')
        self.v=n

class A:
    def __init__(self): self.done=set(); self.calls=[]
    def status(self,k): return TxnStatus.COMMITTED if k in self.done else TxnStatus.UNKNOWN
    def execute(self,k,p): self.calls.append((k,p)); self.done.add(k); return 'ok'

class V3614(unittest.TestCase):
    def states(self):
        cur=SystemState(0,{'alice':{'docs':frozenset({'READ'})}},{'docs':GovernanceRule('docs','root')})
        exp=SystemState(1,{'alice':{'docs':frozenset({'READ','WRITE'})}},{'docs':GovernanceRule('docs','root')})
        gov=SystemState(1,{'alice':{'docs':frozenset({'READ'})}},{'docs':GovernanceRule('docs','alice')})
        return cur,exp,gov
    def test_governance_guard(self):
        cur,_,gov=self.states()
        with self.assertRaisesRegex(PermissionError,'self-governance mutation is not allowed'): validate_transition(cur,gov,'root','docs')
    def test_attenuation_guard(self):
        cur,exp,_=self.states()
        with self.assertRaisesRegex(PermissionError,'permission expansion is not allowed'): validate_transition(cur,exp,'alice','docs')
    def test_recovery_params_binding(self):
        t=EffectTxn('e','k','WRITE',_params_digest({'x':1}))
        a=A()
        with self.assertRaises(AdapterContractError): recover(a,t,{'x':2})
        self.assertEqual(a.calls,[])
    def test_recovery_requires_final_commit(self):
        t=EffectTxn('e','k','WRITE',_params_digest({'x':1}))
        class Unknown(A):
            def status(self,k): return TxnStatus.UNKNOWN
        with self.assertRaises(AdapterContractError): recover(Unknown(),t,{'x':1})
    def test_journal_state_machine(self):
        with tempfile.TemporaryDirectory() as d:
            j=EffectJournal(Path(d)/'e.log',b'x'*32); b={'key':'k','capability_txid':'tx','effect_id':'e','idempotency_key':'k','effect_class':'WRITE','params_digest':'d'}
            j.append({'status':'PREPARED',**b}); bad=dict(b); bad['params_digest']='evil'; j.append({'status':'COMMITTED',**bad})
            with self.assertRaises(ValueError): j.pending()
    def test_anchor_detects_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            sec=b'x'*32; a=Anchor(); p=Path(d)/'s'; s=Store(p,sec,a); base=SystemState(0,{},{}); s._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),base.canonical(),'B')); s._write_atomic(Snapshot(0,1,frozenset({'n'}),frozenset(),tuple(),base.canonical(),'B')); Store(p,sec)._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),base.canonical(),'B'))
            with self.assertRaisesRegex(ValueError,'rollback'): s._read()
    def test_adapter_commit_is_authoritative(self):
        t=EffectTxn('e','k','WRITE',_params_digest({'x':1})); a=A(); self.assertEqual(recover(a,t,{'x':1}),TxnStatus.COMMITTED); self.assertEqual(len(a.calls),1); self.assertEqual(recover(a,t,{'x':1}),TxnStatus.COMMITTED); self.assertEqual(len(a.calls),1)
    def test_store_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            sec=b'x'*32; s=Store(Path(d)/'s',sec); base=SystemState(0,{},{}); s._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),base.canonical(),'B')); self.assertEqual(s._read().boot_id,'B')

if __name__=='__main__': unittest.main()
