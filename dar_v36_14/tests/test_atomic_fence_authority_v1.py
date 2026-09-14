"""Executable reference model for the strong external-fence contract.

This is a model, not evidence that an arbitrary production adapter is atomic.
Its purpose is to make the required serialization contract executable and to
attack the exact interleavings that a deployment must independently verify.
"""
import threading
import unittest

from dar.canonical import canonical_digest
from dar.effect_transaction import FencedEffectAdapter, TxnStatus, AdapterContractError, EffectTxn, protected_commit


class AtomicFenceAuthority(FencedEffectAdapter):
    """Single-authority reference model: fence and effect share one lock."""
    def __init__(self):
        self._lock = threading.Lock()
        self.fences = {}
        self.effects = {}
        self.commit_attempt_hook = None
        self.fail_after_effect = False

    def current_fence(self, outcome_key):
        with self._lock:
            return self.fences.get(outcome_key, 0)

    def advance_fence(self, outcome_key, epoch):
        with self._lock:
            current = self.fences.get(outcome_key, 0)
            if epoch < current:
                raise ValueError("fence rollback")
            self.fences[outcome_key] = epoch

    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        with self._lock:
            if self.commit_attempt_hook:
                self.commit_attempt_hook(self, outcome_key)
            if self.fences.get(outcome_key, 0) != fence_epoch:
                raise RuntimeError("fence advanced")
            if idempotency_key in self.effects:
                return TxnStatus.COMMITTED
            self.effects[idempotency_key] = (outcome_key, dict(params))
            if self.fail_after_effect:
                raise RuntimeError("simulated crash after external commit")
            return TxnStatus.COMMITTED

    def status(self, idempotency_key):
        with self._lock:
            return TxnStatus.COMMITTED if idempotency_key in self.effects else TxnStatus.UNKNOWN

    def execute(self, idempotency_key, params):
        raise AssertionError("unsafe execute path must never be used by protected operations")


class AtomicFenceAuthorityTests(unittest.TestCase):
    def _txn(self, key, outcome, epoch=1, params=None):
        params = {"x": 1} if params is None else params
        return EffectTxn(key, key, "WRITE", canonical_digest(params), outcome, epoch), params

    def test_refusal_versus_commit_serialization(self):
        a = AtomicFenceAuthority()
        outcome = "aa11"
        txn, params = self._txn("k", outcome)
        a.fences[outcome] = 1
        a.advance_fence(outcome, 2)
        with self.assertRaises(AdapterContractError):
            protected_commit(a, txn, params)
        self.assertEqual(a.effects, {})

    def test_commit_wins_before_refusal_then_refusal_cannot_claim_retroactive_no(self):
        a = AtomicFenceAuthority()
        outcome = "bb22"
        txn, params = self._txn("k", outcome)
        a.fences[outcome] = 1
        self.assertEqual(protected_commit(a, txn, params), TxnStatus.COMMITTED)
        self.assertEqual(a.effects["k"][0], outcome)
        a.advance_fence(outcome, 2)
        self.assertEqual(a.current_fence(outcome), 2)
        self.assertIn("k", a.effects)

    def test_crash_after_external_commit_is_unknown_not_no(self):
        a = AtomicFenceAuthority()
        outcome = "cc33"
        txn, params = self._txn("k", outcome)
        a.fences[outcome] = 1
        a.fail_after_effect = True
        with self.assertRaises(AdapterContractError):
            protected_commit(a, txn, params)
        self.assertEqual(a.status("k"), TxnStatus.COMMITTED)

    def test_idempotent_retry_does_not_duplicate_outcome(self):
        a = AtomicFenceAuthority()
        outcome = "dd44"
        txn, params = self._txn("k", outcome)
        a.fences[outcome] = 1
        self.assertEqual(protected_commit(a, txn, params), TxnStatus.COMMITTED)
        self.assertEqual(protected_commit(a, txn, params), TxnStatus.COMMITTED)
        self.assertEqual(len(a.effects), 1)

    def test_adversarial_commit_hook_can_advance_fence_but_atomicity_wins(self):
        a = AtomicFenceAuthority()
        outcome = "ee55"
        txn, params = self._txn("k", outcome)
        a.fences[outcome] = 1

        def try_advance(authority, key):
            authority.fences[key] = 2

        a.commit_attempt_hook = try_advance
        with self.assertRaises(AdapterContractError):
            protected_commit(a, txn, params)
        self.assertEqual(a.effects, {})


if __name__ == "__main__":
    unittest.main()
