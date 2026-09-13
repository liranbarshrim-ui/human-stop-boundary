from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet

class MutationClass(str, Enum):
    NONE='NONE'; PERMISSION_EXPANSION='PERMISSION_EXPANSION'; PERMISSION_CONTRACTION='PERMISSION_CONTRACTION'; GOVERNANCE_MUTATION='GOVERNANCE_MUTATION'; META_GOVERNANCE_MUTATION='META_GOVERNANCE_MUTATION'

@dataclass(frozen=True)
class GovernanceRule:
    domain: str
    controller: str
    governance_admins: FrozenSet[str]=frozenset()
    subordinate_domains: FrozenSet[str]=frozenset()

@dataclass(frozen=True)
class SystemState:
    epoch: int
    permissions: dict = field(default_factory=dict)
    governance: dict = field(default_factory=dict)
    def perms(self,p,d): return frozenset(self.permissions.get(p,{}).get(d,frozenset()))
    def canonical(self):
        return {'epoch':self.epoch,'permissions':{p:{d:sorted(v) for d,v in sorted(ds.items())} for p,ds in sorted(self.permissions.items())},'governance':{d:{'domain':r.domain,'controller':r.controller,'governance_admins':sorted(r.governance_admins),'subordinate_domains':sorted(r.subordinate_domains)} for d,r in sorted(self.governance.items())}}

@dataclass(frozen=True)
class AuthorityDelta:
    changed_permission_pairs: tuple
    changed_governance_domains: tuple
    mutation_class: MutationClass
    @staticmethod
    def derive(a,b):
        pairs=set()
        for s in (a.permissions,b.permissions):
            for p,ds in s.items(): pairs.update((p,d) for d in ds)
        cp=tuple(sorted((p,d) for p,d in pairs if a.perms(p,d)!=b.perms(p,d)))
        cg=tuple(sorted(d for d in set(a.governance)|set(b.governance) if a.governance.get(d)!=b.governance.get(d)))
        meta=any(a.governance.get(d) and b.governance.get(d) and (a.governance[d].governance_admins!=b.governance[d].governance_admins or a.governance[d].subordinate_domains!=b.governance[d].subordinate_domains) for d in cg)
        if meta: mc=MutationClass.META_GOVERNANCE_MUTATION
        elif cg: mc=MutationClass.GOVERNANCE_MUTATION
        elif any(b.perms(p,d)-a.perms(p,d) for p,d in cp): mc=MutationClass.PERMISSION_EXPANSION
        elif cp: mc=MutationClass.PERMISSION_CONTRACTION
        else: mc=MutationClass.NONE
        return AuthorityDelta(cp,cg,mc)
