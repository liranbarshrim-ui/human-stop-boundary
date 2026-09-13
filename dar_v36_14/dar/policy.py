from .model import AuthorityDelta,MutationClass

def closure(state, principal):
    seen=set(); q=[d for d,r in state.governance.items() if r.controller==principal or principal in r.governance_admins]
    while q:
        d=q.pop()
        if d in seen: continue
        seen.add(d); r=state.governance.get(d)
        if r: q.extend(r.subordinate_domains-seen)
    return frozenset(seen)

def has_cycle(governance):
    graph={d:set(r.subordinate_domains) for d,r in governance.items()}
    visiting=set(); done=set()
    def dfs(n):
        if n in visiting: return True
        if n in done: return False
        visiting.add(n)
        if any(x in graph and dfs(x) for x in graph.get(n,())): return True
        visiting.remove(n); done.add(n); return False
    return any(dfs(d) for d in graph)

def validate_transition(current, proposed, principal, domain):
    if proposed.epoch != current.epoch+1: raise PermissionError('epoch must advance by exactly one')
    delta=AuthorityDelta.derive(current,proposed); cl=closure(current,principal)
    if delta.mutation_class == MutationClass.NONE: return delta
    if delta.changed_governance_domains:
        if not set(delta.changed_governance_domains) <= cl: raise PermissionError('governance transition outside closure')
        raise PermissionError('self-governance mutation is not allowed')
    for p,d in delta.changed_permission_pairs:
        added=proposed.perms(p,d)-current.perms(p,d)
        if added: raise PermissionError('permission expansion is not allowed by attenuation-only kernel')
    if has_cycle(proposed.governance): raise PermissionError('governance cycle')
    changed={p for p,_ in delta.changed_permission_pairs}
    if changed and changed != {principal}: raise PermissionError('cross-principal permission mutation')
    return delta
