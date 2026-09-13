import tempfile
import unittest
from pathlib import Path

from dar import Kernel, Snapshot, Store, SystemState, Capability
from dar.effect_gate import EffectDenied, EffectGate, EffectRequest


class RefusalPropertyTests(unittest.TestCase):
    def test_invalid_capability_cannot_reach_executor(self):
        class Never:
            def __call__(self):
                raise AssertionError("executor reached after invalid authorization")

        with tempfile.TemporaryDirectory() as d:
            secret = b"x" * 32
            store = Store(Path(d) / "state", secret)
            base = SystemState(0, {}, {})
            store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), base.canonical(), "B"))
            kernel = Kernel(store, secret, boot_id="B")
            gate = EffectGate(kernel)
            capability = Capability(
                "bad-txid", 0, "bad-nonce", 0, "B", "attacker", "none",
                "WRITE", "WRITE", "NONE", "bad-digest", "bad-mac"
            )
            request = EffectRequest(capability, "attacker", "none", "WRITE", "e", "WRITE")
            with self.assertRaises(EffectDenied):
                gate.execute(request, Never())


if __name__ == "__main__":
    unittest.main()
