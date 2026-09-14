import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dar import Snapshot, Store
from dar.refusal import RefusalAuthority
from dar.effect_transaction import FencedEffectAdapter, TxnStatus, protected_commit, EffectTxn, AdapterContractError
from dar.canonical import canonical_digest

SECRET = b'x' * 32


class RefusalFenceAdapter(FencedEffectAdapter):
    def __init__(self):
        self.fences = {}
        self.refusals = {}
        self.effects = {}

    def current_fence(self, outcome_key):
        return self.fences.get(outcome_key, 0)

    def refuse_outcome(self, outcome_key, epoch, refusal_id):
        current = self.current_fence(outcome_key)
        existing = self.refusals.get(outcome_key)
        if existing:
            if existing != (epoch, refusal_id):
                raise ValueError('conflicting terminal refusal')
            return
        if epoch < current:
            raise ValueError('fence rollback')
        self.fences[outcome_key] = epoch
        self.refusals[outcome_key] = (epoch, refusal_id)

    def is_refused(self, outcome_key):
        return outcome_key in self.refusals

    def advance_fence(self, outcome_key, epoch):
        if self.is_refused(outcome_key):
            raise ValueError('terminal refusal cannot be advanced')
        current = self.current_fence(outcome_key)
        if epoch < current:
            raise ValueError('fence rollback')
        self.fences[outcome_key] = epoch

    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        if self.is_refused(outcome_key):
            raise RuntimeError('outcome terminally refused')
        if self.current_fence(outcome_key) != fence_epoch:
            raise RuntimeError('fence advanced')
        if idempotency_key in self.effects:
            return TxnStatus.COMMITTED
        self.effects[idempotency_key] = (outcome_key, dict(params))
        return TxnStatus.COMMITTED

    def status(self, idempotency_key):
        return TxnStatus.COMMITTED if idempotency_key in self.effects else TxnStatus.UNKNOWN

    def execute(self, idempotency_key, params):
        raise AssertionError('protected path must not use execute')


class RefusalAuthorityTests(unittest.TestCase):
    def make_store(self, root):
        store = Store(Path(root) / 'state', SECRET)
        store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), {'epoch': 0, 'permissions': {}, 'governance': {}}, 'B', tuple(), tuple()))
        return store

    def test_authenticated_refusal_is_bound_to_principal_effect_and_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            store = self.make_store(d)
            auth = RefusalAuthority(store, {'human-a': b'a' * 32, 'human-b': b'b' * 32})
            refusal = auth.issue_protected('human-a', 'effect-1', 'tx-1', 'aabb')
            self.assertTrue(auth.verify(refusal))
            self.assertEqual(refusal.principal, 'human-a')
            self.assertEqual(refusal.effect_id, 'effect-1')
            self.assertEqual(refusal.capability_txid, 'tx-1')
            self.assertEqual(refusal.outcome_key, 'aabb')
            tampered = type(refusal)(refusal.refusal_id, 'human-b', refusal.effect_id, refusal.capability_txid, refusal.target_epoch, refusal.issued_at, refusal.mac, refusal.outcome_key)
            self.assertFalse(auth.verify(tampered))

    def test_commit_persists_refusal_and_advances_epoch(self):
        with tempfile.TemporaryDirectory() as d:
            store = self.make_store(d)
            auth = RefusalAuthority(store, {'human-a': b'a' * 32})
            refusal = auth.issue('human-a', 'effect-1', 'tx-1')
            auth.commit(refusal)
            state = store._read()
            self.assertEqual(state.epoch, refusal.target_epoch)
            self.assertEqual(len(state.state_payload['refusals']), 1)
            self.assertEqual(state.state_payload['refusals'][0]['principal'], 'human-a')

    def test_tampered_refusal_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store = self.make_store(d)
            auth = RefusalAuthority(store, {'human-a': b'a' * 32})
            refusal = auth.issue('human-a', 'effect-1', 'tx-1')
            tampered = type(refusal)(refusal.refusal_id, refusal.principal, 'effect-2', refusal.capability_txid, refusal.target_epoch, refusal.issued_at, refusal.mac, refusal.outcome_key)
            self.assertFalse(auth.verify(tampered))

    def test_external_terminal_refusal_survives_crash_before_local_persistence_and_blocks_new_id(self):
        with tempfile.TemporaryDirectory() as d:
            store = self.make_store(d)
            auth = RefusalAuthority(store, {'human-a': b'a' * 32})
            adapter = RefusalFenceAdapter()
            refusal = auth.issue_protected('human-a', 'effect-1', 'tx-1', 'deadbeef', target_epoch=1)
            real_write = store._write_atomic

            def crash_on_refusal(snapshot):
                if snapshot.state_payload.get('refusals'):
                    raise RuntimeError('simulated crash before durable refusal publication')
                return real_write(snapshot)

            with patch.object(store, '_write_atomic', side_effect=crash_on_refusal):
                with self.assertRaises(RuntimeError):
                    auth.commit_protected(refusal, adapter)

            self.assertTrue(adapter.is_refused('deadbeef'))
            self.assertEqual(store._read().state_payload.get('refusals', []), [])
            txn = EffectTxn('new', 'new', 'WRITE', canonical_digest({'x': 1}), 'deadbeef', 1)
            with self.assertRaises(AdapterContractError):
                protected_commit(adapter, txn, {'x': 1})
            self.assertEqual(adapter.effects, {})

    def test_protected_refusal_retry_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            store = self.make_store(d)
            auth = RefusalAuthority(store, {'human-a': b'a' * 32})
            adapter = RefusalFenceAdapter()
            refusal = auth.issue_protected('human-a', 'effect-1', 'tx-1', 'feed01', target_epoch=1, refusal_id='r1')
            auth.commit_protected(refusal, adapter)
            self.assertTrue(adapter.is_refused('feed01'))
            self.assertEqual(auth.commit_protected(refusal, adapter), refusal)

    def test_external_fence_is_not_retroactive(self):
        with tempfile.TemporaryDirectory() as d:
            store = self.make_store(d)
            auth = RefusalAuthority(store, {'human-a': b'a' * 32})
            adapter = RefusalFenceAdapter()
            refusal = auth.issue_protected('human-a', 'effect-1', 'tx-1', 'feed01', target_epoch=2)
            adapter.fences['feed01'] = 1
            auth.commit_protected(refusal, adapter)
            self.assertEqual(adapter.current_fence('feed01'), 2)
            already_committed = EffectTxn('k', 'k', 'WRITE', canonical_digest({'x': 1}), 'feed01', 1)
            with self.assertRaises(AdapterContractError):
                protected_commit(adapter, already_committed, {'x': 1})
            self.assertEqual(adapter.effects, {})


if __name__ == '__main__':
    unittest.main()
