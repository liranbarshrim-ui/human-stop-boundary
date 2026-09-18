"""Executable local harness for the eight pre-registered A11 escape vectors.

These tests are deliberately repository-local. A PASS here is evidence about the
executed checkout only; it is never an independent A11/A1 conclusion.
"""

import inspect
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from dar import Kernel, Snapshot, Store, SystemState
from dar.boundary import BoundaryDenied, DispatcherClient, PrivilegedDispatcher
from dar.effect_gate import EffectDenied, EffectGate, EffectRequest

SECRET = b"x" * 32
ROOT = Path(__file__).resolve().parents[1]


def make_kernel(root):
    store = Store(Path(root) / "state", SECRET)
    state = SystemState(0, {"human": {"root": frozenset({"WRITE", "READ"})}}, {})
    store._write_atomic(
        Snapshot(0, 0, frozenset(), frozenset(), tuple(), state.canonical(), "B")
    )
    return store, Kernel(store, SECRET, boot_id="B")


def issue_write(kernel, params, effect_id):
    current = kernel._state(kernel.store._read())
    state = SystemState(
        current.epoch + 1,
        {"human": {"root": frozenset({"WRITE", "READ"})}},
        {},
    )
    return kernel.issue(
        "human", "root", "WRITE", state,
        nonce="a11-nonce", params=params, effect_id=effect_id,
    )


# A11-V1 — unauthorized identity -> protected WRITE
# Primary: A11. Secondary: A1.
def test_a11_v1_unauthorized_identity_is_rejected_by_gate():
    with tempfile.TemporaryDirectory() as d:
        _, kernel = make_kernel(d)
        gate = EffectGate(kernel)
        params = {"path": "v1.txt", "data": "blocked"}
        cap = issue_write(kernel, params, "a11-v1")
        req = EffectRequest(cap, "attacker", "root", "WRITE", "a11-v1", "WRITE")
        with pytest.raises(EffectDenied):
            gate.execute(req, lambda: "must-not-run", params)


# A11-V2 — alternate IPC/socket/pipe/queue/shared-memory path
# Primary: A11. Secondary: A1. Exhaustive deployment IPC inventory remains external.
def test_a11_v2_registered_client_is_the_only_declared_local_transport_entrypoint():
    source = inspect.getsource(DispatcherClient)
    assert "def execute(" in source
    assert "self.gate.execute" in source
    assert "socket" not in source and "multiprocessing" not in source


# A11-V3 — helper/child-process delegation
# Primary: A11. Secondary: A1. This probes the public interface in a child process;
# host-level identity isolation still requires independent deployment evidence.
def test_a11_v3_child_process_cannot_use_public_execute_bypass():
    code = (
        "from dar.boundary import PrivilegedDispatcher\n"
        "import tempfile, pathlib\n"
        "with tempfile.TemporaryDirectory() as d:\n"
        " p=PrivilegedDispatcher(pathlib.Path(d)/'b')\n"
        " print(hasattr(p,'execute'))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT,
        text=True, capture_output=True, check=True,
    )
    assert result.stdout.strip() == "False"


# A11-V4 — direct adapter/deprecated/importable interface
# Primary: A11. Secondary: A1. This checks the declared public surface only.
def test_a11_v4_public_dispatcher_has_no_direct_execute_adapter():
    with tempfile.TemporaryDirectory() as d:
        dispatcher = PrivilegedDispatcher(Path(d) / "boundary")
        assert not hasattr(dispatcher, "execute")
        with pytest.raises(AttributeError):
            dispatcher.execute("WRITE", {"path": "v4.txt", "data": "escape"})


# A11-V5 — startup/recovery/reconciliation after refusal
# Primary: A11. Secondary: A1. A terminal refusal blocks the normal protected path.
def test_a11_v5_terminal_refusal_blocks_recovery_entry():
    with tempfile.TemporaryDirectory() as d:
        store, kernel = make_kernel(d)
        gate = EffectGate(kernel)
        params = {"path": "v5.txt", "data": "blocked"}
        cap = issue_write(kernel, params, "a11-v5")
        from dar.refusal import RefusalAuthority
        auth = RefusalAuthority(store, {"human": b"a" * 32})
        auth.commit(auth.issue("human", "a11-v5", cap.txid))
        req = EffectRequest(cap, "human", "root", "WRITE", "a11-v5", "WRITE")
        with pytest.raises(EffectDenied):
            gate.execute(req, lambda: "must-not-run", params)


# A11-V6 — descriptor/path substitution + TOCTOU
# Primary: A11. Secondary: A1. Local path boundary rejects traversal and absolute paths.
def test_a11_v6_path_substitution_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        dispatcher = PrivilegedDispatcher(Path(d) / "boundary")
        with pytest.raises(BoundaryDenied):
            dispatcher._apply("WRITE", {"path": "../escape.txt", "data": "x"})
        with pytest.raises(BoundaryDenied):
            dispatcher._apply("WRITE", {"path": "/absolute.txt", "data": "x"})


# A11-V7 — network/plugin/side-channel route
# Primary: A11. Secondary: A1. Source inspection cannot prove complete deployment topology.
def test_a11_v7_registered_dispatcher_has_no_network_plugin_entrypoint():
    source = inspect.getsource(PrivilegedDispatcher)
    assert "socket" not in source
    assert "subprocess" not in source
    assert "plugin" not in source.lower()


# A11-V8 — local rollback -> fresh protected commit
# Primary: A11. Secondary: A9. External-anchor existence remains an independent condition.
def test_a11_v8_rollback_cannot_restore_authority_past_external_anchor_floor():
    class Anchor:
        def __init__(self): self.value = 0
        def floor(self): return self.value
        def advance_to(self, sequence): self.value = max(self.value, sequence)

    with tempfile.TemporaryDirectory() as d:
        anchor = Anchor()
        store = Store(Path(d) / "state", SECRET, anchor=anchor)
        state = SystemState(0, {"human": {"root": frozenset({"WRITE"})}}, {})
        store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), state.canonical(), "B"))
        with pytest.raises(ValueError):
            store._write_atomic(
                Snapshot(0, -1, frozenset(), frozenset(), tuple(), state.canonical(), "B")
            )
