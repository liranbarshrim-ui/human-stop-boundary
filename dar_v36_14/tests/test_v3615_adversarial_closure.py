import tempfile
import threading
import unittest
from pathlib import Path

from dar import EffectGate, EffectRequest, Kernel, Snapshot, Store, SystemState
from dar.effect_journal import EffectJournal
from dar.effect_transaction import TxnStatus

SECRET=b'x'*32

class Adapter:
    def __init__(self): self.calls=[]; self.done=set()
    def execute(self,key,params): self.calls.append((key,params)); self.done.add(key); return 'ok'
    def status(self,key): return TxnStatus.COMMITTED if key in self.done else TxnStatus.UNKNOWN

class BrokenJournal:
    def append(self,record):
        if record['status']=='PREPARED': raise OSError('injected prepare failure')

class V3615AdversarialClosure(unittest.TestCase):
    def make(self, root, anchor=None):
        store=Store(Path(root)/'state',SECRET,anchor=anchor)
        state=SystemState(0,{'human':{'root':frozenset({'WRITE','READ'})}},{})
        store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),state.canonical(),'B',tuple(),tuple()))
        kernel=Kernel(store,SECRET,boot_id='B')
        return store,kernel,EffectGate(kernel)

    def issue_write(self,kernel,params):
        state=SystemState(1,{'human':{'root':frozenset({'WRITE','READ'})}},{} )
        return kernel.issue('human','root','WRITE',state,nonce='n1',params=params)

    def advance_refusal_epoch(self,store):
        with store.tx():
            s=store._read()
            state=dict(s.state_payload); state['epoch']=s.epoch+1
            store._write_atomic(Snapshot(s.epoch+1,s.sequence+1,s.nonces,s.consumed,s.commits,state,s.boot_id,s.effects,s.pending_effects))

    def test_pending_created_after_refusal_is_not_reconciled(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel,gate=self.make(d)
            params={'path':'pending.txt','data':'x'}; cap=self.issue_write(kernel,params)
            req=EffectRequest(cap,'human','root','WRITE','pending','WRITE')
            adapter=Adapter()
            with self.assertRaises(OSError): gate.execute_recoverable(req,adapter,params,BrokenJournal())
            self.assertEqual(len(store._read().pending_effects),1)
            self.advance_refusal_epoch(store)
            real=EffectJournal(Path(d)/'effects.log',SECRET)
            self.assertEqual(gate.reconcile_pending(adapter,real,lambda i:params),1)
            self.assertEqual(adapter.calls,[])
            self.assertEqual(store._read().pending_effects,())

    def test_recoverable_pending_mutation_advances_monotonic_sequence(self):
        class Anchor:
            def __init__(self): self.value=0
            def floor(self): return self.value
            def advance_to(self,sequence): self.value=max(self.value,sequence)
        with tempfile.TemporaryDirectory() as d:
            anchor=Anchor(); store,kernel,gate=self.make(d,anchor=anchor)
            params={'path':'seq.txt','data':'x'}; cap=self.issue_write(kernel,params)
            before=store._read().sequence
            req=EffectRequest(cap,'human','root','WRITE','seq','WRITE')
            with self.assertRaises(OSError): gate.execute_recoverable(req,Adapter(),params,BrokenJournal())
            after=store._read().sequence
            self.assertEqual(after,before+1)
            self.assertEqual(anchor.floor(),after)
            self.assertGreater(after,before)

    def test_execute_refusal_race_has_single_linearization_order(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel,gate=self.make(d)
            params={'path':'race.txt','data':'x'}; cap=self.issue_write(kernel,params)
            req=EffectRequest(cap,'human','root','WRITE','race','WRITE')
            started=threading.Event(); release=threading.Event(); result=[]
            def executor():
                started.set(); release.wait(2); result.append('executed'); return 'ok'
            t=threading.Thread(target=lambda: gate.execute(req,executor,params)); t.start()
            self.assertTrue(started.wait(2))
            refusal_done=[]
            def refuse():
                self.advance_refusal_epoch(store); refusal_done.append(True)
            r=threading.Thread(target=refuse); r.start()
            # Refusal must block while the protected executor owns the store
            # transaction, so it cannot linearize between authorization and execution.
            self.assertFalse(refusal_done)
            release.set(); t.join(2); r.join(2)
            self.assertEqual(result,['executed'])
            self.assertTrue(refusal_done)
            self.assertEqual(store._read().epoch,2)

if __name__=='__main__': unittest.main()
