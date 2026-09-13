import fcntl,hashlib,hmac,json,os,tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

def write_all(fd,data):
    mv=memoryview(data); off=0
    while off<len(mv):
        n=os.write(fd,mv[off:])
        if n<=0: raise OSError('short/zero write')
        off+=n

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()

class MonotonicAnchor(Protocol):
    """Trusted monotonic floor outside the Store rollback domain."""
    def floor(self) -> int: ...
    def advance_to(self, sequence: int) -> None: ...

@dataclass(frozen=True)
class Snapshot:
    epoch:int; sequence:int; nonces:frozenset; consumed:frozenset; commits:tuple; state_payload:dict; boot_id:str; effects:tuple=frozenset(); pending_effects:tuple=frozenset()

class Store:
    def __init__(self,path,secret,anchor=None):
        self.path=Path(path); self.secret=secret; self.anchor=anchor; self.lock=Path(str(self.path)+'.lock'); self.path.parent.mkdir(parents=True,exist_ok=True); self.path.parent.chmod(0o700); self.lock.touch(exist_ok=True); self.lock.chmod(0o600); self.path.touch(exist_ok=True); self.path.chmod(0o600)
    def tx(self):
        class T:
            def __enter__(slf):
                slf.fd=os.open(self.lock,os.O_RDWR); fcntl.flock(slf.fd,fcntl.LOCK_EX); return slf
            def __exit__(slf,*a): fcntl.flock(slf.fd,fcntl.LOCK_UN); os.close(slf.fd)
        return T()
    def _wrap(self,obj):
        raw=canon(obj); return canon({'payload':obj,'mac':hmac.new(self.secret,raw,hashlib.sha256).hexdigest()})
    def _read(self):
        try:
            raw=self.path.read_bytes()
            if not raw: raise ValueError
            w=json.loads(raw); p=w['payload']; mac=w['mac']
            if not hmac.compare_digest(mac,hmac.new(self.secret,canon(p),hashlib.sha256).hexdigest()): raise ValueError('store MAC failure')
            snap=Snapshot(int(p['epoch']),int(p['sequence']),frozenset(p['nonces']),frozenset(p['consumed']),tuple(p['commits']),p['state_payload'],p['boot_id'],tuple(p.get('effects',())),tuple(p.get('pending_effects',())))
            if self.anchor is not None and snap.sequence < self.anchor.floor(): raise ValueError('store rollback detected')
            return snap
        except FileNotFoundError: pass
        return Snapshot(0,0,frozenset(),frozenset(),tuple(),{'epoch':0,'permissions':{},'governance':{}},'',tuple(),tuple())
    def _write_atomic(self,s):
        p=self.path
        if self.anchor is not None:
            floor=self.anchor.floor()
            if s.sequence < floor: raise ValueError('store sequence below monotonic anchor')
            if s.sequence > floor: self.anchor.advance_to(s.sequence)
        fd,tmp=tempfile.mkstemp(prefix=p.name+'.',dir=p.parent); os.fchmod(fd,0o600)
        try:
            write_all(fd,self._wrap({'epoch':s.epoch,'sequence':s.sequence,'nonces':sorted(s.nonces),'consumed':sorted(s.consumed),'commits':list(s.commits),'state_payload':s.state_payload,'boot_id':s.boot_id,'effects':list(s.effects),'pending_effects':list(s.pending_effects)})); os.fsync(fd); os.close(fd); os.replace(tmp,p); dfd=os.open(p.parent,os.O_RDONLY); os.fsync(dfd); os.close(dfd)
        finally:
            try: os.unlink(tmp)
            except FileNotFoundError: pass
    def rebind_boot(self, boot_id):
        with self.tx():
            try: s=self._read()
            except ValueError:
                if self.path.exists() and self.path.stat().st_size == 0: s=Snapshot(0,0,frozenset(),frozenset(),tuple(),{'epoch':0,'permissions':{},'governance':{}},'',tuple(),tuple())
                else: raise
            self._write_atomic(Snapshot(s.epoch,s.sequence,s.nonces,s.consumed,s.commits,s.state_payload,boot_id,s.effects,s.pending_effects))
