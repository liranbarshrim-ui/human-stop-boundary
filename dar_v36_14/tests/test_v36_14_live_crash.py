import os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from dar import GovernanceRule,Kernel,Snapshot,Store,SystemState
from dar.effect_gate import EffectRequest
from dar.process_dispatcher import UnixDispatcherClient,BoundaryDenied

class LiveCrashBoundary(unittest.TestCase):
    def test_sigkill_rotates_generation_and_rejects_old_capability(self):
        with tempfile.TemporaryDirectory() as td:
            b=Path(td); root=b/'effects'; root.mkdir(); ipc=b/'ipc'; ipc.mkdir(); state=b/'state.json'; secret_file=b/'secret'; secret=b'v36.14-live-secret-012345678901234567'; secret_file.write_bytes(secret); secret_file.chmod(0o600)
            boot='B'*64; store=Store(state,secret); model=SystemState(0,{'alice':{'docs':frozenset({'READ'})}},{'docs':GovernanceRule('docs','root')}); store._write_atomic(Snapshot(0,0,frozenset(),frozenset(),tuple(),model.canonical(),boot))
            launcher=Path(__file__).resolve().parents[1]/'run_privileged_server.py'; env=dict(os.environ); env['PYTHONPATH']=str(launcher.parent)
            cmd=[sys.executable,str(launcher),'--socket',str(ipc/'dar.sock'),'--root',str(root),'--state',str(state),'--secret-file',str(secret_file),'--allowed-uid',str(os.getuid())]
            def start():
                p=subprocess.Popen(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                for _ in range(200):
                    if p.poll() is not None: raise RuntimeError(p.stderr.read())
                    if (ipc/'dar.sock').exists():
                        import socket
                        try:
                            q=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); q.settimeout(.05); q.connect(str(ipc/'dar.sock')); q.close(); return p
                        except OSError: pass
                    time.sleep(.01)
                p.kill(); raise RuntimeError('server did not start')
            p=start()
            try:
                current=Store(state,secret)._read(); cap=Kernel(Store(state,secret),secret,boot_id=current.boot_id).issue('alice','docs','READ',SystemState(1,{'alice':{'docs':frozenset({'READ'})}},{'docs':GovernanceRule('docs','root')}),'live-crash-nonce')
            finally:
                os.kill(p.pid,signal.SIGKILL); p.wait(timeout=3)
            p2=start()
            try:
                req=EffectRequest(cap,'alice','docs','READ','old-cap','READ')
                with self.assertRaises(BoundaryDenied): UnixDispatcherClient(str(ipc/'dar.sock')).execute(req,{'path':'missing'})
            finally:
                os.kill(p2.pid,signal.SIGTERM); p2.wait(timeout=3)

if __name__=='__main__': unittest.main()
