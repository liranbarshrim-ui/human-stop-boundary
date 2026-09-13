#!/usr/bin/env python3
"""Live two-UID A-06 boundary test.

Run in a privileged Linux test environment where `daemon` and `nobody` exist.
The dispatcher runs as `daemon`; `nobody` is the unauthorized identity.
"""
import json
import os
import pwd
import subprocess
import tempfile
import time
from pathlib import Path

from dar.store import Store, Snapshot
from dar.model import SystemState, GovernanceRule
from dar.kernel import Kernel

D = pwd.getpwnam("daemon")
N = pwd.getpwnam("nobody")
t = tempfile.TemporaryDirectory()
b = Path(t.name)
os.chmod(b, 0o711)
os.chown(b, D.pw_uid, D.pw_gid)
root = b / "effects"
ipc = b / "ipc"
stated = b / "state"
root.mkdir(); ipc.mkdir(); stated.mkdir()
for p in (root, ipc, stated):
    os.chown(p, D.pw_uid, D.pw_gid)
os.chmod(root, 0o700)
os.chmod(ipc, 0o711)
os.chmod(stated, 0o700)

state = stated / "state.json"
secretf = stated / "secret"
secret = b"v36.14-live-secret-012345678901234567"
boot = "L" * 64
store = Store(str(state), secret)
base = SystemState(
    0,
    {"alice": {"docs": frozenset({"READ", "WRITE"})}},
    {"docs": GovernanceRule("docs", "root")},
)
store._write_atomic(Snapshot(0, 0, frozenset(), frozenset(), tuple(), base.canonical(), boot))
secretf.write_bytes(secret)
os.chmod(secretf, 0o600)

proposed = SystemState(
    1,
    {"alice": {"docs": frozenset({"READ", "WRITE"})}},
    {"docs": GovernanceRule("docs", "root")},
)
params = {"path": "via.txt", "data": "OK"}
cap = Kernel(Store(str(state), secret), secret, boot_id=boot).issue(
    "alice", "docs", "WRITE", proposed, "nonce-live", params=params
)
for p in (state, Path(str(state) + ".lock"), secretf):
    os.chown(p, D.pw_uid, D.pw_gid)

sock = ipc / "dar.sock"
env = os.environ.copy()
env.pop("DAR_PRIVILEGED_LAUNCHER", None)
launcher = Path(os.environ.get("DAR_PRIVILEGED_LAUNCHER", "/tmp/dar-run-privileged-server.py"))

def as_uid(uid, gid, args):
    return subprocess.run(
        args,
        env=env,
        preexec_fn=lambda: (os.setgid(gid), os.setuid(uid)),
        capture_output=True,
        text=True,
        timeout=5,
    )

p = subprocess.Popen(
    [
        "python3", str(launcher),
        "--socket", str(sock), "--root", str(root), "--state", str(state),
        "--secret-file", str(secretf), "--allowed-uid", str(D.pw_uid),
        "--boot-id", boot, "--seccomp",
    ],
    env=env,
    preexec_fn=lambda: (os.setgid(D.pw_gid), os.setuid(D.pw_uid)),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
try:
    for _ in range(100):
        if sock.exists(): break
        if p.poll() is not None:
            raise RuntimeError(p.stderr.read())
        time.sleep(0.02)
    assert sock.exists()
    checks = []

    # Exact regression test for the original A-06 flaw: the unprivileged
    # process imports the class and attempts the old direct public API.
    direct_api_code = (
        "from dar.boundary import PrivilegedDispatcher; "
        f"d=PrivilegedDispatcher({str(root)!r}); "
        "assert not hasattr(d,'execute'); "
        "getattr(d,'execute')('WRITE',{'path':'direct-api.txt','data':'PWN'})"
    )
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", direct_api_code])
    checks.append(("unprivileged direct import + old execute denied", r.returncode != 0 and not (root / "direct-api.txt").exists()))

    # The package may be readable by the unprivileged identity for client use,
    # but its privileged resources remain OS-protected.
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", "from dar.boundary import PrivilegedDispatcher; print(PrivilegedDispatcher.__name__)"])
    checks.append(("unprivileged can import package but has no public privileged endpoint", r.returncode == 0))

    # Unauthorized identity: OS-level access to protected resources must fail.
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", f"open({str(root/'x')!r},'w').write('PWN')"])
    checks.append(("direct effect write denied", r.returncode != 0 and not (root / "x").exists()))
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", f"open({str(secretf)!r},'rb').read()"])
    checks.append(("secret read denied", r.returncode != 0))
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", f"open({str(state)!r},'rb').read()"])
    checks.append(("state read denied", r.returncode != 0))
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", f"open({str(state)!r},'ab').write(b'x')"])
    checks.append(("state write denied", r.returncode != 0))
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", f"import os; os.unlink({str(sock)!r})"])
    checks.append(("socket replacement denied", r.returncode != 0 and sock.exists()))
    r = as_uid(N.pw_uid, N.pw_gid, ["python3", "-c", f"import socket; s=socket.socket(socket.AF_UNIX); s.connect({str(sock)!r})"])
    checks.append(("unauthorized socket connect denied", r.returncode != 0))

    capj = json.dumps(cap.__dict__)
    valid_code = (
        f"import json; from dar.kernel import Capability; from dar.effect_gate import EffectRequest; "
        f"from dar.process_dispatcher import UnixDispatcherClient; "
        f"c=Capability(**json.loads({capj!r})); r=EffectRequest(c,'alice','docs','WRITE','e1','WRITE'); "
        f"print(UnixDispatcherClient({str(sock)!r}).execute(r,{{'path':'via.txt','data':'OK'}}))"
    )
    r = as_uid(D.pw_uid, D.pw_gid, ["python3", "-c", valid_code])
    checks.append(("authorized IPC effect works", r.returncode == 0 and (root / "via.txt").read_text() == "OK"))

    forged_code = (
        f"import json; from dar.kernel import Capability; from dar.effect_gate import EffectRequest; "
        f"from dar.process_dispatcher import UnixDispatcherClient; "
        f"c=Capability(**json.loads({capj!r})); r=EffectRequest(c,'alice','docs','WRITE','e2','WRITE'); "
        f"print(UnixDispatcherClient({str(sock)!r}).execute(r,{{'path':'via.txt','data':'FORGED'}}))"
    )
    r = as_uid(D.pw_uid, D.pw_gid, ["python3", "-c", forged_code])
    checks.append(("parameter substitution rejected", r.returncode != 0 and (root / "via.txt").read_text() == "OK"))

    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    if not all(ok for _, ok in checks):
        raise SystemExit(1)
finally:
    if p.poll() is None:
        p.terminate()
        p.wait(timeout=2)
