import tempfile, unittest
from pathlib import Path
from dar import *
from dar.effect_journal import EffectJournal
from dar.effect_transaction import TxnStatus
from dar.effect_gate import EffectRequest

class Adapter:
    def __init__(self): self.calls=[]; self.done=set()
    def status(self,k): return TxnStatus.COMMITTED if k in self.done else TxnStatus.UNKNOWN
    def execute(self,k,p): self.calls.append((k,p)); self.done.add(k); return 'ok'

class BrokenJournal:
    def __init__(self, fail_status=None): self.fail_status=fail_status; self.calls=[]
    def append(self,r):
        self.calls.append(r)
        if r['status']==self.fail_status: raise OSError('injected journal failure')
    def _validated_state(self):
        state={}
        for r in self.calls:
            if r['status']=='PREPARED': state[r['key']]=r
            elif r['status']=='COMMITTED': state[r['key']]=r
        return state

class V3613(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory(); sec=b'z'*32
        self.store=Store(Path(self.d.name)/'state.json',sec); self.k=Kernel(self.store,sec,boot_id='B'*64); self.g=EffectGate(self.k)
        s=SystemState(0,{'alice':{'docs':frozenset({'READ'})}},{'docs':GovernanceRule('docs','root')})
        self.store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),s.canonical(),'B'*64))
    def tearDown(self): self.d.cleanup()
    def cap(self):
        p=SystemState(1,{'alice':{'docs':frozenset({'READ'})}},{'docs':GovernanceRule('docs','root')})
        return self.k.issue('alice','docs','READ',p,'n1')
    def req(self,c): return EffectRequest(c,'alice','docs','READ','e1','READ')
    def test_capability_consumption_and_intent_are_one_store_commit(self):
        c=self.cap(); a=Adapter(); j=BrokenJournal('PREPARED')
        with self.assertRaises(OSError): self.g.execute_recoverable(self.req(c),a,{'x':1},j)
        self.assertEqual(a.calls, []); self.assertEqual(len(self.store._read().pending_effects),1); self.assertTrue(c.txid in self.store._read().consumed)
    def test_commit_journal_failure_leaves_durable_intent(self):
        c=self.cap(); a=Adapter(); j=BrokenJournal('COMMITTED')
        with self.assertRaises(OSError): self.g.execute_recoverable(self.req(c),a,{'x':1},j)
        s=self.store._read(); self.assertEqual(len(s.pending_effects),1); self.assertEqual(a.calls, [(f'{c.txid}:e1', {'x':1})])
    def test_reconcile_pending_after_commit_journal_failure(self):
        c=self.cap(); a=Adapter(); j=BrokenJournal('COMMITTED')
        with self.assertRaises(OSError): self.g.execute_recoverable(self.req(c),a,{'x':1},j)
        real=EffectJournal(Path(self.d.name)/'effects.log', b'z'*32); intent=self.store._read().pending_effects[0]
        real.append({'status':'PREPARED', **intent})
        self.assertEqual(self.g.reconcile_pending(a, real, lambda i:{'x':1}), 1)
        self.assertEqual(self.store._read().pending_effects, ())
        self.assertEqual(real._validated_state()[intent['key']]['status'], 'COMMITTED')
        self.assertEqual(a.calls, [(f'{c.txid}:e1', {'x':1})])
    def test_replay_cannot_create_different_intent_after_commit_failure(self):
        c=self.cap(); a=Adapter(); j=BrokenJournal('COMMITTED')
        with self.assertRaises(OSError): self.g.execute_recoverable(self.req(c),a,{'x':1},j)
        with self.assertRaises(EffectDenied): self.g.execute_recoverable(self.req(c),Adapter(),{'x':2},BrokenJournal())

if __name__=='__main__': unittest.main()
