import tempfile
import unittest
from pathlib import Path

from dar import GovernanceRule, Kernel, Snapshot, Store, SystemState
from dar.effect_gate import EffectGate, EffectRequest
from dar.effect_transaction import AdapterContractError, EffectTxn, TxnStatus, _params_digest, recover
from dar.policy import validate_transition


class MemoryAnchor:
    def __init__(self): self.value = 0
    def floor(self): return self.value
    def advance_to(self, sequence):
        if sequence < self.value: raise ValueError('anchor rollback')
        self.value = sequence


class V3614Integrity(unittest.TestCase):
    def _states(self):
        cur = SystemState(0, {'alice': {'docs': frozenset({'READ'})}}, {'docs': GovernanceRule('docs', 'root')})
        same = SystemState(1, {'alice': {'docs': frozenset({'READ'})}}, {'docs': GovernanceRule('docs', 'root')})
        write = SystemState(1, {'alice': {'docs': frozenset({'READ', 'WRITE'})}}, {'docs': GovernanceRule('docs', 'root')})
        gov = SystemState(1, {'alice': {'docs': frozenset({'READ'})}}, {'docs': GovernanceRule('docs', 'alice')})
        return cur, same, write, gov

    def test_governance_guard_is_reached_when_domain_is_in_closure(self):
        cur, _, _, gov = self._states()
        with self.assertRaisesRegex(PermissionError, 'self-governance mutation is not allowed'):
            validate_transition(cur, gov, 'root', 'docs')

    def test_attenuation_guard_is_reached_for_authorized_principal(self):
        cur, _, write, _ = self._states()
        with self.assertRaisesRegex(PermissionError, 'permission expansion is not allowed'):
            validate_transition(cur, write, 'alice', 'docs')

    def test_recovery_digest_is_binding(self):
        txn = EffectTxn('e', 'k', 'WRITE', _params_digest({'x': 1}))
        class A:
            def status(self, k): return TxnStatus.UNKNOWN
            def execute(self, k, p): raise AssertionError('must not execute')
        with self.assertRaises(AdapterContractError): recover(A(), txn, {'x': 2})

    def test_false_commit_is_rejected(self):
        txn = EffectTxn('e', 'k', 'WRITE', _params_digest({'x': 1}))
        class A:
            def status(self, k): return TxnStatus.UNKNOWN
            def execute(self, k, p): return 'ok'
        with self.assertRaises(AdapterContractError): recover(A(), txn, {'x': 1})

    def test_monotonic_anchor_detects_store_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            sec = b'x' * 32; anchor = MemoryAnchor(); path = Path(d) / 'state.json'
            store = Store(path, sec, anchor=anchor); base = SystemState(0, {}, {})
            store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), base.canonical(), 'B'))
            store._write_atomic(Snapshot(0, 1, frozenset({'n'}), frozenset(), tuple(), base.canonical(), 'B'))
            self.assertEqual(anchor.floor(), 1)
            rollback = Store(path, sec)
            rollback._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), base.canonical(), 'B'))
            with self.assertRaisesRegex(ValueError, 'rollback'): store._read()

    def test_monotonic_anchor_detects_effect_state_rollback_at_same_issue_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            sec = b'x' * 32; anchor = MemoryAnchor(); path = Path(d) / 'state.json'
            store = Store(path, sec, anchor=anchor); base = SystemState(0, {'alice': {'docs': frozenset({'READ'})}}, {'docs': GovernanceRule('docs', 'root')})
            store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), base.canonical(), 'B'))
            store._write_atomic(Snapshot(0, 1, frozenset({'n'}), frozenset(), tuple(), base.canonical(), 'B'))
            store._write_atomic(Snapshot(0, 2, frozenset({'n'}), frozenset({'tx:e'}), tuple(), base.canonical(), 'B', ('tx:e',)))
            self.assertEqual(anchor.floor(), 2)
            rollback = Store(path, sec)
            rollback._write_atomic(Snapshot(0, 1, frozenset({'n'}), frozenset(), tuple(), base.canonical(), 'B'))
            with self.assertRaisesRegex(ValueError, 'rollback'): store._read()

    def test_effect_execution_advances_monotonic_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            sec = b'x' * 32; anchor = MemoryAnchor(); path = Path(d) / 'state.json'
            store = Store(path, sec, anchor=anchor)
            cur = SystemState(0, {'alice': {'docs': frozenset({'READ'})}}, {'docs': GovernanceRule('docs', 'root')})
            store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), cur.canonical(), 'B' * 64))
            k = Kernel(store, sec, boot_id='B' * 64)
            p = SystemState(1, {'alice': {'docs': frozenset({'READ'})}}, {'docs': GovernanceRule('docs', 'root')})
            cap = k.issue('alice', 'docs', 'READ', p, 'n'); before = store._read().sequence
            EffectGate(k).execute(EffectRequest(cap, 'alice', 'docs', 'READ', 'e', 'READ'), lambda: 'ok')
            self.assertEqual(store._read().sequence, before + 1); self.assertEqual(anchor.floor(), before + 1)

    def test_journal_rejects_duplicate_prepare_and_reordering(self):
        from dar.effect_journal import EffectJournal
        with tempfile.TemporaryDirectory() as d:
            j = EffectJournal(Path(d) / 'effects.log', b'z' * 32)
            base = {'key': 'k', 'capability_txid': 'tx', 'effect_id': 'e', 'idempotency_key': 'k', 'effect_class': 'WRITE', 'params_digest': 'd'}
            j.append({'status': 'PREPARED', **base}); j.append({'status': 'PREPARED', **base})
            with self.assertRaises(ValueError): j.pending()


if __name__ == '__main__': unittest.main()
