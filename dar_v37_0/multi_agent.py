"""DAR Multi-Agent (DAR-MA) reference model.

This module models outcome-level refusal authority for distributed multi-agent
systems. It is intentionally a small, dependency-free reference model rather
than a claim of complete distributed-systems enforcement.
"""
from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Mapping, Optional, Tuple


class DARMAError(ValueError):
    pass


@dataclass(frozen=True)
class OutcomeContract:
    outcome_id: str
    scope: str
    authority: str
    prohibited_after_stop: bool = True


@dataclass(frozen=True)
class StopEpoch:
    outcome_id: str
    epoch: int
    stopped_by: str
    reason: str = ""


@dataclass(frozen=True)
class Delegation:
    parent: str
    child: str
    outcomes: FrozenSet[str]
    epoch: int


@dataclass(frozen=True)
class OutcomeEdge:
    source: str
    target: str
    outcomes: FrozenSet[str] = frozenset()
    stop_enforcement: bool = False


@dataclass(frozen=True)
class OutcomeGraph:
    nodes: FrozenSet[str]
    edges: Tuple[OutcomeEdge, ...]

    def paths_to(self, outcome_node: str) -> Tuple[Tuple[str, ...], ...]:
        """Enumerate simple paths to a target in the finite reference graph."""
        if outcome_node not in self.nodes:
            raise DARMAError("unknown outcome node")
        adjacency = {}
        for edge in self.edges:
            adjacency.setdefault(edge.source, []).append(edge)
        sources = sorted(self.nodes - {e.target for e in self.edges})
        paths = []

        def walk(node, path):
            if node == outcome_node:
                paths.append(tuple(path))
                return
            for edge in adjacency.get(node, ()):
                if edge.target in path:
                    continue
                walk(edge.target, path + [edge.target])

        for source in sources:
            walk(source, [source])
        return tuple(paths)

    def has_stop_cut(self, outcome_id: str) -> bool:
        """Return whether every simple path to outcome_id crosses enforcement."""
        for path in self.paths_to(outcome_id):
            edge_pairs = set(zip(path, path[1:]))
            if not any(
                edge.stop_enforcement and (edge.source, edge.target) in edge_pairs
                for edge in self.edges
            ):
                return False
        return True


@dataclass
class MultiAgentBoundary:
    contracts: Mapping[str, OutcomeContract]
    current_epoch: int = 0
    stops: dict = field(default_factory=dict)
    delegations: list = field(default_factory=list)

    def stop(self, authority: str, outcome_id: str, reason: str = "") -> StopEpoch:
        contract = self.contracts.get(outcome_id)
        if contract is None:
            raise DARMAError("unknown outcome")
        if authority != contract.authority:
            raise PermissionError("authority is not the named outcome authority")
        self.current_epoch += 1
        record = StopEpoch(outcome_id, self.current_epoch, authority, reason)
        self.stops[outcome_id] = record
        return record

    def delegate(self, parent: str, child: str, outcomes: Iterable[str], epoch: int) -> Delegation:
        requested = frozenset(outcomes)
        if not requested:
            raise DARMAError("delegation must contain an outcome")
        parent_caps = [d.outcomes for d in self.delegations if d.child == parent and d.epoch >= epoch]
        if parent_caps:
            allowed = frozenset().union(*parent_caps)
        else:
            allowed = frozenset(self.contracts)
        if not requested <= allowed:
            raise PermissionError("delegation widens outcome authority")
        if any(o in self.stops and epoch <= self.stops[o].epoch for o in requested):
            raise PermissionError("delegation uses an outcome revoked at an active stop epoch")
        d = Delegation(parent, child, requested, epoch)
        self.delegations.append(d)
        return d

    def can_execute(self, actor: str, outcome_id: str, epoch: int) -> bool:
        if outcome_id not in self.contracts:
            return False
        stop = self.stops.get(outcome_id)
        if stop is not None and epoch <= stop.epoch:
            return False
        return any(d.child == actor and outcome_id in d.outcomes and epoch > d.epoch for d in self.delegations) or actor == self.contracts[outcome_id].authority

    def verify_graph(self, graph: OutcomeGraph, outcome_id: str) -> None:
        if outcome_id not in self.contracts:
            raise DARMAError("unknown outcome")
        if not graph.has_stop_cut(outcome_id):
            raise DARMAError("declared outcome lacks a human-stop cut")
