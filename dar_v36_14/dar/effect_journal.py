import fcntl, hashlib, hmac, json, os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Intent:
    key: str; capability_txid: str; effect_id: str; idempotency_key: str; effect_class: str; params_digest: str

class EffectJournal:
    def __init__(self, path, secret):
        self.path=Path(path); self.secret=secret; self.lock=Path(str(self.path)+'.lock')
        self.path.parent.mkdir(parents=True,exist_ok=True); self.path.parent.chmod(0o700)
        self.lock.touch(exist_ok=True); self.lock.chmod(0o600)
        if not self.path.exists(): self.path.touch(); self.path.chmod(0o600)
    def _mac(self,payload):
        raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
        return hmac.new(self.secret,raw,hashlib.sha256).hexdigest()
    def _append_locked(self,rec):
        payload=dict(rec); line=json.dumps({'payload':payload,'mac':self._mac(payload)},sort_keys=True,separators=(',',':')).encode()+b'\n'
        fd=os.open(self.path,os.O_WRONLY|os.O_APPEND)
        try:
            off=0
            while off<len(line):
                n=os.write(fd,line[off:])
                if n<=0: raise OSError('short write')
                off+=n
            os.fsync(fd)
        finally: os.close(fd)
    def append(self,rec):
        fd=os.open(self.lock,os.O_RDWR)
        try: fcntl.flock(fd,fcntl.LOCK_EX); self._append_locked(rec)
        finally: fcntl.flock(fd,fcntl.LOCK_UN); os.close(fd)
    def records(self):
        if not self.path.exists(): return []
        out=[]
        for lineno,line in enumerate(self.path.read_bytes().splitlines(),1):
            if not line: continue
            obj=json.loads(line); p=obj['payload']; mac=obj['mac']
            if not hmac.compare_digest(mac,self._mac(p)): raise ValueError(f'journal MAC failure line {lineno}')
            out.append(p)
        return out
    _IMMUTABLE_FIELDS=('capability_txid','effect_id','idempotency_key','effect_class','params_digest')
    def _validated_state(self):
        state={}
        for r in self.records():
            key=r.get('key'); status=r.get('status')
            if not key or status not in ('PREPARED','COMMITTED'): raise ValueError('invalid journal record')
            if status=='PREPARED':
                if key in state: raise ValueError('duplicate PREPARED transition')
                missing=[f for f in self._IMMUTABLE_FIELDS if f not in r]
                if missing: raise ValueError(f'missing PREPARED fields: {missing}')
                state[key]=r; continue
            previous=state.get(key)
            if previous is None or previous.get('status')!='PREPARED': raise ValueError('invalid COMMITTED transition')
            for field in self._IMMUTABLE_FIELDS:
                if r.get(field)!=previous.get(field): raise ValueError(f'COMMITTED field mismatch: {field}')
            state[key]=r
        return state
    def pending(self):
        return [r for r in self._validated_state().values() if r['status']=='PREPARED']
