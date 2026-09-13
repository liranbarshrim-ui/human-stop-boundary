import tempfile
import unittest
from pathlib import Path

from dar import Kernel, Snapshot, Store, SystemState
from dar.effect_gate import EffectDenied, EffectGate, EffectRequest


class RefusalPropertyTests(unittest.TestCase):
    def test_invalid_capability_cannot_reach_executor(self):
        class Never:
            def __call__(self):
                raise AssertionError("executor reached after invalid authorization")

        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / "state", b"x" * 32)
            base = SystemState(0, {}, {})
            store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), base.canonical(), "B"))
            gate = EffectGate(Kernel(store))
            request = EffectRequest(object(), "attacker", "none", "WRITE", "e", "WRITE")
            with self.assertRaises(EffectDenied):
                gate.execute(request, Never())


if __name__ == "__main__":
    unittest.main()
