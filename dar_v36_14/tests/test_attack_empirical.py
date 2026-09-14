import json
import tempfile
import threading
import unittest
from pathlib import Path
from dar import Kernel, Snapshot, Store, SystemState
from dar.boundary import BoundaryDenied, PrivilegedDispatcher
from dar.effect_gate import EffectDenied, EffectGate, EffectRequest
from dar.canonical import CanonicalizationError, canonical_bytes, canonical_digest, canonical_effect_id, parse_json_object
from dar.refusal import RefusalAuthority
SECRET=b"x"*32

def make_kernel(root,*,anchor=None):
    store=Store(Path(root)/"state",SECRET,anchor=anchor); state=SystemState(0,{"human":{"root":frozenset({"WRITE","READ"})}},{}); store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),state.canonical(),"B")); return store,Kernel(store,SECRET,boot_id="B")

def issue_write(kernel,params,effect_id,nonce="n1"):
    current=kernel._state(kernel.store._read()); state=SystemState(current.epoch+1,{"human":{"root":frozenset({"WRITE","READ"})}},{}); return kernel.issue("human","root","WRITE",state,nonce=nonce,params=params,effect_id=effect_id)

class AttackEmpiricalTests(unittest.TestCase):
    def test_a01_refusal_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"a01.txt","data":"ok"}; cap=issue_write(kernel,p,"a01"); req=EffectRequest(cap,"human","root","WRITE","a01","WRITE"); called=[]; gate.execute(req,lambda:called.append(True),p); self.assertEqual(called,[True]); self.assertIn(f"{cap.txid}:a01",store._read().effects)
    def test_a02_refusal_execute_race(self):
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"a02.txt","data":"ok"}; cap=issue_write(kernel,p,"a02"); req=EffectRequest(cap,"human","root","WRITE","a02","WRITE"); results=[]; lock=threading.Lock()
            def run():
                try: gate.execute(req,lambda:"executed",p); value="EXECUTED"
                except EffectDenied: value="DENIED"
                with lock: results.append(value)
            ts=[threading.Thread(target=run) for _ in range(2)]; [t.start() for t in ts]; [t.join() for t in ts]; self.assertEqual(results.count("EXECUTED"),1); self.assertEqual(results.count("DENIED"),1)
    def test_a03_replay_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"a03.txt","data":"ok"}; cap=issue_write(kernel,p,"a03"); req=EffectRequest(cap,"human","root","WRITE","a03","WRITE"); gate.execute(req,lambda:"ok",p)
            with self.assertRaises(EffectDenied): gate.execute(req,lambda:"should-not-run",p)
    def test_a04_stale_capability_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"a04.txt","data":"ok"}; cap=issue_write(kernel,p,"a04"); state=SystemState(2,{"human":{"root":frozenset({"WRITE","READ"})}},{}); kernel.issue("human","root","WRITE",state,nonce="n2",params=p,effect_id="a04-next"); req=EffectRequest(cap,"human","root","WRITE","a04","WRITE")
            with self.assertRaises(EffectDenied): gate.execute(req,lambda:"stale",p)
    def test_a05_rollback_requires_external_monotonic_anchor(self):
        class Anchor:
            def __init__(self): self.value=0
            def floor(self): return self.value
            def advance_to(self,sequence): self.value=max(self.value,sequence)
        with tempfile.TemporaryDirectory() as d:
            anchor=Anchor(); store,kernel=make_kernel(d,anchor=anchor); issue_write(kernel,{"path":"a05.txt","data":"ok"},"a05"); self.assertGreaterEqual(anchor.floor(),1)
            with self.assertRaises(ValueError): store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),SystemState(0,{}).canonical(),"B"))
    def test_a06_alternate_interface_has_no_public_execute(self):
        with tempfile.TemporaryDirectory() as d:
            dispatcher=PrivilegedDispatcher(Path(d)/"boundary")
            self.assertFalse(hasattr(dispatcher,"execute"))
            with self.assertRaises(AttributeError): dispatcher.execute("WRITE",{"path":"alternate.txt","data":"outside gate"})
            self.assertFalse((Path(d)/"boundary"/"alternate.txt").exists())
    def test_a07_confused_deputy_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"a07.txt","data":"ok"}; cap=issue_write(kernel,p,"a07"); req=EffectRequest(cap,"attacker","root","WRITE","a07","WRITE")
            with self.assertRaises(EffectDenied): gate.execute(req,lambda:"deputy",p)
    def test_a08_parameter_substitution_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); bound={"path":"a08.txt","data":"authorized"}; substituted={"path":"a08.txt","data":"attacker"}; cap=issue_write(kernel,bound,"a08"); req=EffectRequest(cap,"human","root","WRITE","a08","WRITE")
            with self.assertRaises(EffectDenied): gate.execute(req,lambda:"should-not-run",substituted)
    def test_a08_canonicalization_is_order_stable(self):
        self.assertEqual(canonical_bytes({"b":1,"a":2}),canonical_bytes({"a":2,"b":1})); self.assertEqual(canonical_digest({"b":1,"a":2}),canonical_digest({"a":2,"b":1}))
    def test_a08_canonicalization_unicode_nfc(self):
        composed="é"; decomposed="e\u0301"; self.assertEqual(canonical_bytes({"text":composed}),canonical_bytes({"text":decomposed})); self.assertEqual(canonical_digest({"text":composed}),canonical_digest({"text":decomposed}))
    def test_a08_canonicalization_rejects_ambiguous_numbers(self):
        with self.assertRaises(CanonicalizationError): canonical_bytes({"x":1.5})
        with self.assertRaises(CanonicalizationError): canonical_bytes({"x":float("nan")})
    def test_a08_canonicalization_rejects_unicode_colliding_keys(self):
        with self.assertRaises(CanonicalizationError): canonical_bytes({"é":1,"e\u0301":2})
    def test_a08_transport_rejects_duplicate_keys(self):
        with self.assertRaises(CanonicalizationError): parse_json_object('{"a":1,"a":2}')
        self.assertEqual(parse_json_object('{"a":1,"b":2}'),{"a":1,"b":2})
    def test_a09_recovery_replay_is_guarded_by_consumption(self):
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"a09.txt","data":"ok"}; cap=issue_write(kernel,p,"a09"); req=EffectRequest(cap,"human","root","WRITE","a09","WRITE"); gate.execute(req,lambda:"first",p)
            with self.assertRaises(EffectDenied): gate.execute(req,lambda:"recovery-replay",p)
    def test_a10_tampered_store_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=make_kernel(d); issue_write(kernel,{"path":"a10.txt","data":"ok"},"a10"); path=Path(d)/"state"; raw=json.loads(path.read_text()); raw["payload"]["sequence"]=999; path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError): store._read()
    def test_a11_false_success_requires_authoritative_status_in_recoverable_path(self):
        from dar.effect_transaction import AdapterContractError
        class Adapter:
            def execute(self,key,params): return "claimed-success"
            def status(self,key): return "UNKNOWN"
        class Journal:
            def append(self,record): pass
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"x","data":"y"}; cap=issue_write(kernel,p,"a11"); req=EffectRequest(cap,"human","root","WRITE","a11","WRITE")
            with self.assertRaises(AdapterContractError): gate.execute_recoverable(req,Adapter(),p,Journal())
    def test_a12_boundary_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            dispatcher=PrivilegedDispatcher(Path(d)/"boundary")
            with self.assertRaises(BoundaryDenied): dispatcher._apply("WRITE",{"path":"../escape.txt","data":"x"})
            with self.assertRaises(BoundaryDenied): dispatcher._apply("WRITE",{"path":"/absolute.txt","data":"x"})
    def test_a13_effect_id_is_bound_to_capability(self):
        with tempfile.TemporaryDirectory() as d:
            _,kernel=make_kernel(d); gate=EffectGate(kernel); p={"path":"same.txt","data":"same"}; cap=issue_write(kernel,p,"wire-001")
            forged=EffectRequest(cap,"human","root","WRITE","wire-002","WRITE")
            with self.assertRaises(EffectDenied): gate.execute(forged,lambda:"should-not-run",p)
    def test_a14_effect_id_is_nfc_canonical_across_issue_refuse_and_gate(self):
        with tempfile.TemporaryDirectory() as d:
            store,kernel=make_kernel(d); gate=EffectGate(kernel); auth=RefusalAuthority(store,{"human":b"a"*32}); p={"path":"a14.txt","data":"same"}
            with self.assertRaises(CanonicalizationError): canonical_effect_id("cafe\u0301")
            cap=issue_write(kernel,p,"cafe-1")
            refusal=auth.issue("human","cafe-1",cap.txid); auth.commit(refusal)
            cap2=issue_write(kernel,p,"cafe-1",nonce="n2")
            req=EffectRequest(cap2,"human","root","WRITE","cafe-1","WRITE")
            with self.assertRaises(EffectDenied): gate.execute(req,lambda:"should-not-run",p)
    def test_a15_effect_id_rejects_ambiguous_unicode_and_control_input(self):
        bad_ids=("wіre-001","wıre-001","wire-\u200b001","wire-\u200d001","wire-001\u0000","wire-001\u007f"," wire-001","wire-001 ","wire-001\t","wire-001\n","café","cafe\u0301")
        for value in bad_ids:
            with self.assertRaises(CanonicalizationError): canonical_effect_id(value)
        for value in ("wire-001","payment.v2:001","a0b1c2","A0B1C2"):
            self.assertEqual(canonical_effect_id(value),value)

if __name__ == '__main__': unittest.main()
