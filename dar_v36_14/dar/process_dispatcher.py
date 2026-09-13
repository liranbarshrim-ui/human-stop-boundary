import json, os, socket, struct, secrets, fcntl
from .boundary import PrivilegedDispatcher, BoundaryDenied
from .canonical import CanonicalizationError, parse_json_object
from .effect_gate import EffectGate, EffectRequest
from .kernel import Capability
MAX_FRAME=64*1024
class UnixDispatcherServer:
    def __init__(self,socket_path,root,store,secret,allowed_uid=None,boot_id=None):
        self.socket_path=socket_path; self.root=os.path.realpath(root); self.allowed_uid=os.getuid() if allowed_uid is None else int(allowed_uid)
        self.dispatcher=PrivilegedDispatcher(self.root)
        from .kernel import Kernel
        self.boot_id=boot_id or secrets.token_hex(32); self.kernel=Kernel(store,secret,boot_id=self.boot_id); self.gate=EffectGate(self.kernel)
        self._daemon_lock_path=self.kernel.store.path.with_name(self.kernel.store.path.name+'.daemon.lock'); self._daemon_lock_fd=None
    @staticmethod
    def _peer_uid(conn):
        if not hasattr(socket,'SO_PEERCRED'): raise BoundaryDenied('SO_PEERCRED unavailable')
        raw=conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize('3i')); _pid,uid,_gid=struct.unpack('3i',raw); return uid
    @staticmethod
    def _recv_frame(conn):
        hdr=bytearray()
        while len(hdr)<4:
            chunk=conn.recv(4-len(hdr))
            if not chunk: raise BoundaryDenied('invalid frame header')
            hdr.extend(chunk)
        n=struct.unpack('!I',hdr)[0]
        if n==0 or n>MAX_FRAME: raise BoundaryDenied('invalid frame length')
        buf=bytearray()
        while len(buf)<n:
            chunk=conn.recv(min(16384,n-len(buf)))
            if not chunk: raise BoundaryDenied('truncated frame')
            buf.extend(chunk)
        try: return parse_json_object(bytes(buf).decode('utf-8'))
        except CanonicalizationError as exc: raise BoundaryDenied(str(exc)) from exc
    @staticmethod
    def _send_frame(conn,obj):
        data=json.dumps(obj,separators=(',',':')).encode('utf-8')
        if len(data)>MAX_FRAME: raise BoundaryDenied('response too large')
        conn.sendall(struct.pack('!I',len(data))+data)
    @staticmethod
    def _cap(obj):
        fields=('txid','sequence','nonce','epoch','boot_id','principal','domain','action','effect_class','mutation_class','state_digest','mac','params_digest')
        if not isinstance(obj,dict) or set(obj)!=set(fields): raise BoundaryDenied('invalid capability shape')
        return Capability(*(obj[x] for x in fields))
    def handle(self,conn):
        if self._peer_uid(conn)!=self.allowed_uid: raise BoundaryDenied('peer uid denied')
        req=self._recv_frame(conn)
        if not isinstance(req,dict) or set(req)!={'capability','principal','domain','action','effect_id','effect_class','params'}: raise BoundaryDenied('invalid request shape')
        cap=self._cap(req['capability']); er=EffectRequest(cap,req['principal'],req['domain'],req['action'],req['effect_id'],req['effect_class'])
        result=self.gate.execute(er,lambda:self.dispatcher._apply(er.effect_class,req['params']),req['params'])
        self._send_frame(conn,{'ok':True,'result':result})
    def _acquire_daemon_lock(self):
        if self._daemon_lock_fd is not None: return
        fd=os.open(self._daemon_lock_path,os.O_RDWR|os.O_CREAT,0o600)
        try: os.fchmod(fd,0o600); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: os.close(fd); raise BoundaryDenied('another dispatcher instance is already active')
        self._daemon_lock_fd=fd
    def _release_daemon_lock(self):
        if self._daemon_lock_fd is not None:
            try: fcntl.flock(self._daemon_lock_fd,fcntl.LOCK_UN)
            finally: os.close(self._daemon_lock_fd); self._daemon_lock_fd=None
    def _bind_generation(self):
        self.kernel.store.rebind_boot(self.boot_id)
        from .kernel import Kernel
        self.kernel=Kernel(self.kernel.store,self.kernel.secret,boot_id=self.boot_id); self.gate=EffectGate(self.kernel)
    def serve_forever(self):
        self._acquire_daemon_lock(); self._bind_generation()
        parent=os.path.dirname(os.path.realpath(self.socket_path)) or '.'; os.makedirs(parent,mode=0o711,exist_ok=True); os.chmod(parent,0o711)
        try: os.unlink(self.socket_path)
        except FileNotFoundError: pass
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.settimeout(1); s.bind(self.socket_path); os.chmod(self.socket_path,0o660); s.listen(32)
        if getattr(self,'enable_seccomp',False) or getattr(self,'enable_landlock',False):
            from .hardening import install_no_new_privs; install_no_new_privs()
        if getattr(self,'enable_seccomp',False):
            from .hardening import install_dispatcher_seccomp; install_dispatcher_seccomp()
        if getattr(self,'enable_landlock',False):
            from .hardening import install_landlock; install_landlock(self.root,os.path.dirname(os.path.realpath(self.kernel.store.path)))
        try:
            while True:
                try: conn,_=s.accept()
                except socket.timeout: continue
                conn.settimeout(5)
                try: self.handle(conn)
                except Exception as e:
                    try: self._send_frame(conn,{'ok':False,'error':type(e).__name__+': '+str(e)})
                    except Exception: pass
                finally: conn.close()
        finally:
            s.close()
            try: os.unlink(self.socket_path)
            except FileNotFoundError: pass
            self._release_daemon_lock()
    def serve_once(self):
        parent=os.path.dirname(os.path.realpath(self.socket_path)) or '.'; os.makedirs(parent,mode=0o711,exist_ok=True); os.chmod(parent,0o711)
        try: os.unlink(self.socket_path)
        except FileNotFoundError: pass
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.settimeout(5); s.bind(self.socket_path); os.chmod(self.socket_path,0o660); s.listen(8)
        try:
            conn,_=s.accept(); conn.settimeout(5)
            try: self.handle(conn)
            except Exception as e:
                try: self._send_frame(conn,{'ok':False,'error':type(e).__name__+': '+str(e)})
                except Exception: pass
            finally: conn.close()
        finally: s.close(); self._release_daemon_lock()
class UnixDispatcherClient:
    def __init__(self,socket_path): self.socket_path=socket_path
    @staticmethod
    def _frame(obj):
        data=json.dumps(obj,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        if len(data)>MAX_FRAME: raise BoundaryDenied('request too large')
        return struct.pack('!I',len(data))+data
    def execute(self,req,params):
        c=req.capability; fields=('txid','sequence','nonce','epoch','boot_id','principal','domain','action','effect_class','mutation_class','state_digest','mac','params_digest')
        cap={k:getattr(c,k) for k in fields}; msg={'capability':cap,'principal':req.principal,'domain':req.domain,'action':req.action,'effect_id':req.effect_id,'effect_class':req.effect_class,'params':params}
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.settimeout(5)
        try:
            s.connect(self.socket_path); s.sendall(self._frame(msg)); hdr=bytearray()
            while len(hdr)<4:
                chunk=s.recv(4-len(hdr))
                if not chunk: raise BoundaryDenied('invalid response')
                hdr.extend(chunk)
            n=struct.unpack('!I',hdr)[0]
            if n==0 or n>MAX_FRAME: raise BoundaryDenied('invalid response length')
            data=bytearray()
            while len(data)<n:
                chunk=s.recv(min(16384,n-len(data)))
                if not chunk: raise BoundaryDenied('truncated response')
                data.extend(chunk)
            out=parse_json_object(bytes(data).decode('utf-8'))
            if not out.get('ok'): raise BoundaryDenied(out.get('error','denied'))
            return out['result']
        except CanonicalizationError as exc: raise BoundaryDenied(str(exc)) from exc
        finally: s.close()
