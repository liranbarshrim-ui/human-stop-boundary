import hashlib,hmac,json,secrets,uuid
from dataclasses import dataclass
from .model import SystemState
from .policy import validate_transition
from .store import Snapshot

@dataclass(frozen=True)
class Capability:
    txid:str; sequence:int; nonce:str; epoch:int; boot_id:str
    principal:str; domain:str; action:str; effect_class:str
    mutation_class:str; state_digest:str; mac:str

class Kernel:
    def __init__(self,store,secret,boot_id=None): self.store=store; self.secret=secret; self.boot_id=boot_id or secrets.token_hex(32)
    def _digest(self,state): return hashlib.sha256(json.dumps(state.canonical(),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    def _mac(self,*x): return hmac.new(self.secret,'|'.join(map(str,x)).encode(),hashlib.sha256).hexdigest()
    def _state(self,s):
        from .model import GovernanceRule
        p=s.state_payload
        return SystemState(int(p['epoch']),{x:{d:frozenset(v) for d,v in ds.items()} for x,ds in p['permissions'].items()},{d:GovernanceRule(r['domain'],r['controller'],frozenset(r['governance_admins']),frozenset(r['subordinate_domains'])) for d,r in p['governance'].items()})
    @staticmethod
    def _effect_class(action):
        allowed={'READ','WRITE','NETWORK','PROCESS'}
        if action not in allowed: raise PermissionError(f'unsupported action/effect class: {action}')
        return action
    def issue(self,principal,domain,action,proposed,nonce=None):
        nonce=nonce or secrets.token_hex(32); effect_class=self._effect_class(action)
        with self.store.tx():
            s=self.store._read()
            if s.boot_id and s.boot_id!=self.boot_id: raise RuntimeError('boot identity mismatch')
            cur=self._state(s)
            if action not in cur.perms(principal,domain): raise PermissionError('effect action is not authorized for principal/domain')
            if action not in proposed.perms(principal,domain): raise PermissionError('proposed state removes requested effect authorization')
            delta=validate_transition(cur,proposed,principal,domain)
            if nonce in s.nonces: raise ValueError('nonce replay')
            seq=s.sequence+1; txid=str(uuid.uuid4()); sd=self._digest(proposed)
            mac=self._mac(txid,seq,nonce,proposed.epoch,self.boot_id,principal,domain,action,effect_class,delta.mutation_class.value,sd)
            cap=Capability(txid,seq,nonce,proposed.epoch,self.boot_id,principal,domain,action,effect_class,delta.mutation_class.value,sd,mac)
            commit={'txid':txid,'sequence':seq,'nonce':nonce,'epoch':proposed.epoch,'principal':principal,'domain':domain,'action':action,'effect_class':effect_class,'mutation_class':delta.mutation_class.value,'state_digest':sd}
            self.store._write_atomic(Snapshot(proposed.epoch,seq,s.nonces|{nonce},s.consumed,s.commits+(commit,),proposed.canonical(),self.boot_id,s.effects,s.pending_effects))
            return cap
    def verify_locked(self,cap,principal,domain,action,effect_class,s):
        if (cap.boot_id!=self.boot_id or cap.principal!=principal or cap.domain!=domain or cap.action!=action or cap.effect_class!=effect_class or cap.epoch!=s.epoch): return False
        exp=self._mac(cap.txid,cap.sequence,cap.nonce,cap.epoch,cap.boot_id,cap.principal,cap.domain,cap.action,cap.effect_class,cap.mutation_class,cap.state_digest)
        if not hmac.compare_digest(exp,cap.mac): return False
        return any(r['txid']==cap.txid and r['sequence']==cap.sequence and r['nonce']==cap.nonce and r['state_digest']==cap.state_digest and r.get('effect_class',r.get('action'))==cap.effect_class for r in s.commits)
