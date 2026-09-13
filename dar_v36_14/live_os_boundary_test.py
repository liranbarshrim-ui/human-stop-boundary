#!/usr/bin/env python3
"""Optional live two-UID boundary smoke test.

Run as a privileged test environment where `daemon` and `nobody` accounts exist.
"""
import os,pwd,tempfile,subprocess,time,json
from pathlib import Path
from dar.store import Store,Snapshot
from dar.model import SystemState,GovernanceRule
from dar.kernel import Kernel
D=pwd.getpwnam('daemon'); N=pwd.getpwnam('nobody')
t=tempfile.TemporaryDirectory(); b=Path(t.name); os.chmod(b,0o711); os.chown(b,D.pw_uid,D.pw_gid)
root=b/'effects'; ipc=b/'ipc'; stated=b/'state'; root.mkdir(); ipc.mkdir(); stated.mkdir()
for p in (root,ipc,stated): os.chown(p,D.pw_uid,D.pw_gid)
os.chmod(root,0o700); os.chmod(ipc,0o711); os.chmod(stated,0o700)
state=stated/'state.json'; secretf=stated/'secret'; secret=b'v36.14-live-secret-012345678901234567'; boot='L'*64
store=Store(str(state),secret); base=SystemState(0,{'alice':{'docs':frozenset({'READ','WRITE'})}},{'docs':GovernanceRule('docs','root')}); store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),base.canonical(),boot))
secretf.write_bytes(secret); os.chmod(secretf,0o600)
proposed=SystemState(1,{'alice':{'docs':frozenset({'READ','WRITE'})}},{'docs':GovernanceRule('docs','root')}); cap=Kernel(Store(str(state),secret),secret,boot_id=boot).issue('alice','docs','WRITE',proposed,'nonce-live')
os.chown(state,D.pw_uid,D.pw_gid); os.chown(Path(str(state)+'.lock'),D.pw_uid,D.pw_gid); os.chown(secretf,D.pw_uid,D.pw_gid)
sock=ipc/'dar.sock'; env=os.environ.copy(); HERE=Path(__file__).resolve().parent; env['PYTHONPATH']=str(HERE); launcher=str(HERE/'run_privileged_server.py')
p=subprocess.Popen(['python3',launcher,'--socket',str(sock),'--root',str(root),'--state',str(state),'--secret-file',str(secretf),'--allowed-uid',str(N.pw_uid),'--boot-id',boot,'--seccomp'],env=env,preexec_fn=lambda:(os.setgid(D.pw_gid),os.setuid(D.pw_uid)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
for _ in range(100):
    if sock.exists(): break
    if p.poll() is not None: raise RuntimeError(p.stderr.read())
    time.sleep(.02)
assert sock.exists()
capj=json.dumps(cap.__dict__); checks=[]
def agent(code): return subprocess.run(['python3','-c',code],env=env,preexec_fn=lambda:(os.setgid(N.pw_gid),os.setuid(N.pw_uid)),capture_output=True,text=True,timeout=5)
r=agent(f"open({str(root/'x')!r},'w').write('PWN')"); checks.append(('direct effect write denied',r.returncode!=0 and not (root/'x').exists()))
r=agent(f"open({str(secretf)!r},'rb').read()"); checks.append(('secret read denied',r.returncode!=0))
r=agent(f"open({str(state)!r},'rb').read()"); checks.append(('state read denied',r.returncode!=0))
r=agent(f"import os; os.unlink({str(sock)!r})"); checks.append(('socket replacement denied',r.returncode!=0 and sock.exists()))
code=f"import json; from dar.kernel import Capability; from dar.effect_gate import EffectRequest; from dar.process_dispatcher import UnixDispatcherClient; c=Capability(**json.loads({capj!r})); r=EffectRequest(c,'alice','docs','WRITE','e1','WRITE'); print(UnixDispatcherClient({str(sock)!r}).execute(r,{{'path':'via.txt','data':'OK'}}))"
r=agent(code); checks.append(('authorized IPC effect works',r.returncode==0 and (root/'via.txt').read_text()=='OK'))
r=agent(f"import socket,struct; s=socket.socket(socket.AF_UNIX); s.connect({str(sock)!r}); s.sendall(struct.pack('!I',1)+b'x'); print(s.recv(4096).decode())"); checks.append(('malformed request rejected',r.returncode==0 and 'ok":false' in r.stdout))
for name,ok in checks: print(('PASS ' if ok else 'FAIL ')+name)
if p.poll() is None: p.terminate(); p.wait(timeout=2)
if not all(ok for _,ok in checks): raise SystemExit(1)
