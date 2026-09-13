import os
from dataclasses import dataclass

class BoundaryDenied(Exception): pass

@dataclass(frozen=True)
class EffectTicket:
    capability: object
    effect_id: str
    effect_class: str

class PrivilegedDispatcher:
    """No caller-supplied Python callable crosses the effect boundary."""
    ALLOWED={'READ':'read_file','WRITE':'write_file'}
    def __init__(self,root):
        self.root=os.path.realpath(root); os.makedirs(self.root,mode=0o700,exist_ok=True); os.chmod(self.root,0o700)
    def _components(self,rel):
        if not isinstance(rel,str) or rel.startswith('/') or '\x00' in rel: raise BoundaryDenied('invalid path')
        parts=[x for x in rel.split('/') if x not in ('','.')]
        if not parts or any(x=='..' for x in parts): raise BoundaryDenied('path escape')
        return parts
    def _open_read(self,rel):
        parts=self._components(rel); nofollow=getattr(os,'O_NOFOLLOW',0)
        rootfd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|nofollow); dirfd=rootfd
        try:
            for part in parts[:-1]:
                newfd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|nofollow,dir_fd=dirfd)
                if dirfd!=rootfd: os.close(dirfd)
                dirfd=newfd
            return os.fdopen(os.open(parts[-1],os.O_RDONLY|nofollow,dir_fd=dirfd),'rb')
        except Exception:
            if dirfd!=rootfd:
                try: os.close(dirfd)
                except OSError: pass
            raise
        finally: os.close(rootfd)
    def _open_write(self,rel):
        parts=self._components(rel)
        if len(parts)!=1: raise BoundaryDenied('nested paths not enabled')
        rootfd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|getattr(os,'O_NOFOLLOW',0))
        try: return os.fdopen(os.open(parts[0],os.O_WRONLY|os.O_CREAT|os.O_TRUNC|getattr(os,'O_NOFOLLOW',0),0o600,dir_fd=rootfd),'w',encoding='utf-8')
        finally: os.close(rootfd)
    def execute(self,effect_class,params):
        if effect_class not in self.ALLOWED: raise BoundaryDenied('undeclared effect')
        if not isinstance(params,dict): raise BoundaryDenied('invalid params')
        if effect_class=='READ':
            with self._open_read(params.get('path','')) as f: return f.read().decode('utf-8')
        if effect_class=='WRITE':
            data=params.get('data')
            if not isinstance(data,str): raise BoundaryDenied('invalid data')
            with self._open_write(params.get('path','')) as f: f.write(data); f.flush(); os.fsync(f.fileno())
            return 'ok'
        raise BoundaryDenied('unimplemented')

class DispatcherClient:
    def __init__(self,gate,dispatcher): self.gate=gate; self.dispatcher=dispatcher
    def execute(self,req,params):
        if req.effect_class not in self.dispatcher.ALLOWED: raise BoundaryDenied('undeclared effect')
        return self.gate.execute(req,lambda:self.dispatcher.execute(req.effect_class,params))
