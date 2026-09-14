"""Executable reference model for the strong external-fence contract.

This is a model, not evidence that an arbitrary production adapter is atomic.
Its purpose is to make the required serialization contract executable and to
attack refusal/commit interleavings, crashes, retries, and rollback.
"""
import threading
import unittest

from dar.canonical import canonical_digest
from dar.effect_transaction import FencedEffectAdapter, TxnStatus, AdapterContractError, EffectTxn, protected_commit


class AtomicFenceAuthority(FencedEffectAdapter):
    """Single-authority reference model: fence, refusal and effect share one lock."""
    def __init__(self):
        self._lock = threading.Lock()
        self.fences = {}
        self.refusals = {}
        self.effects = {}
        self.commit_attempt_hook = None
        self.fail_after_effect = False
        self.fail_after_refusal = False

    def current_fence(self, outcome_key):
        with self._lock:
            return self.fences.get(outcome_key, 0)

    def advance_fence(self, outcome_key, epoch):
        with self._lock:
            if outcome_key in self.refusals:
                raise ValueError("terminal refusal cannot be cleared or advanced")
            current = self.fences.get(outcome_key, 0)
            if epoch < current:
                raise ValueError("fence rollback")
            self.fences[outcome_key] = epoch

    def refuse_outcome(self, outcome_key, fence_epoch, refusal_id):
        with self._lock:
            current = self.fences.get(outcome_key, 0)
            if current > fence_epoch:
                raise ValueError("refusal fence rollback")
            existing = self.refusals.get(outcome_key)
            if existing:
                if existing != (fence_epoch, refusal_id):
                    raise ValueError("conflicting refusal")
                return
            self.fences[outcome_key] = fence_epoch
            self.refusals[outcome_key] = (fence_epoch, refusal_id)
            if self.fail_after_refusal:
                raise RuntimeError("simulated crash after external refusal")

    def is_refused(self, outcome_key):
        with self._lock:
            return outcome_key in self.refusals

    def commit(self, idempotency_key, outcome_key, fence_epoch, params):
        with self._lock:
            if self.commit_attempt_hook:
                self.commit_attempt_hook(self, outcome_key)
            if outcome_key in self.refusals:
                raise RuntimeError("outcome terminally refused")
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

    def test_terminal_refusal_blocks_same_epoch_and_new_idempotency_key(self):
        a = AtomicFenceAuthority()
        outcome = "ff66"
        a.refuse_outcome(outcome, 1, "r1")
        txn, params = self._txn("new-key", outcome, 1)
        with self.assertRaises(AdapterContractError):
            protected_commit(a, txn, params)
        self.assertEqual(a.effects, {})

    def test_refusal_retry_is_idempotent(self):
        a = AtomicFenceAuthority()
        outcome = "1122"
        a.refuse_outcome(outcome, 3, "r1")
        a.refuse_outcome(outcome, 3, "r1")
        self.assertTrue(a.is_refused(outcome))
        self.assertEqual(a.current_fence(outcome), 3)
        self.assertEqual(a.refusals[outcome], (3, "r1"))

    def test_refusal_is_terminal_across_later_epochs(self):
        a = AtomicFenceAuthority()
        outcome = "3344"
        a.refuse_outcome(outcome, 2, "r1")
        with self.assertRaises(ValueError):
            a.advance_fence(outcome, 3)
        txn, params = self._txn("later", outcome, 2)
        with self.assertRaises(AdapterContractError):
            protected_commit(a, txn, params)

    def test_crash_after_external_refusal_is_still_terminal(self):
        a = AtomicFenceAuthority()
        outcome = "5566"
        a.fail_after_refusal = True
        with self.assertRaises(RuntimeError):
            a.refuse_outcome(outcome, 4, "r1")
        self.assertTrue(a.is_refused(outcome))
        txn, params = self._txn("after-crash", outcome, 4)
        with self.assertRaises(AdapterContractError):
            protected_commit(a, txn, params)

    def test_refusal_marker_is_not_rolled_back_by_numeric_fence_update(self):
        a = AtomicFenceAuthority()
        outcome = "7788"
        a.refuse_outcome(outcome, 5, "r1")
        with self.assertRaises(ValueError):
            a.advance_fence(outcome, 4)
        self.assertTrue(a.is_refused(outcome))


if __name__ == "__main__":
    unittest.main()
