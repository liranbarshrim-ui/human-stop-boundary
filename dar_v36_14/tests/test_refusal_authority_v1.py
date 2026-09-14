import tempfile
import unittest
from pathlib import Path

from dar import Snapshot, Store
from dar.refusal import RefusalAuthority

SECRET = b'x' * 32


class RefusalAuthorityTests(unittest.TestCase):
    def make_store(self, root):
        store = Store(Path(root) / 'state', SECRET)
        store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), {'epoch': 0, 'permissions': {}, 'governance': {}}, 'B', tuple(), tuple()))
        return store

    def test_authenticated_refusal_is_bound_to_principal_and_effect(self):
        with tempfile.TemporaryDirectory() as d:
            store = self.make_store(d)
            auth = RefusalAuthority(store, {'human-a': b'a' * 32, 'human-b': b'b' * 32})
            refusal = auth.issue('human-a', 'effect-1', 'tx-1')
            self.assertTrue(auth.verify(refusal))
            self.assertEqual(refusal.principal, 'human-a')
            self.assertEqual(refusal.effect_id, 'effect-1')
            self.assertEqual(refusal.capability_txid, 'tx-1')
            self.assertFalse(auth.verify(type(refusal)(refusal.refusal_id, 'human-b', refusal.effect_id, refusal.capability_txid, refusal.target_epoch, refusal.issued_at, refusal.mac)))

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
            tampered = type(refusal)(refusal.refusal_id, refusal.principal, 'effect-2', refusal.capability_txid, refusal.target_epoch, refusal.issued_at, refusal.mac)
            self.assertFalse(auth.verify(tampered))


if __name__ == '__main__':
    unittest.main()
