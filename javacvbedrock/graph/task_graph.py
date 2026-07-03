"""Dependency graph primitives for staged conversion work."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Mapping

from javacvbedrock.diagnostics import ConversionLog
from javacvbedrock.errors import TaskGraphError


class TaskKind(StrEnum):
    DISCOVERY = "discovery"
    LOADING = "loading"
    PARSING = "parsing"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    OPTIMIZATION = "optimization"
    GENERATION = "generation"
    PACKAGING = "packaging"


@dataclass(frozen=True, slots=True)
class TaskResult:
    outputs: Mapping[str, object]
    log: ConversionLog


@dataclass(frozen=True, slots=True)
class TaskNode:
    id: str
    kind: TaskKind
    dependencies: frozenset[str] = frozenset()
    run: Callable[[], TaskResult] | None = None


@dataclass(slots=True)
class TaskGraph:
    nodes: dict[str, TaskNode] = field(default_factory=dict)

    def add(self, node: TaskNode) -> None:
        if node.id in self.nodes:
            raise TaskGraphError(f"Task node already exists: {node.id}")
        missing = node.dependencies.difference(self.nodes)
        if missing:
            raise TaskGraphError(f"Task node {node.id} has unknown dependencies: {sorted(missing)}")
        self.nodes[node.id] = node

    def topological_order(self) -> tuple[TaskNode, ...]:
        incoming = {node_id: len(node.dependencies) for node_id, node in self.nodes.items()}
        outgoing: dict[str, list[str]] = defaultdict(list)
        for node in self.nodes.values():
            for dependency in node.dependencies:
                outgoing[dependency].append(node.id)

        ready = deque(node_id for node_id, count in incoming.items() if count == 0)
        ordered: list[TaskNode] = []
        while ready:
            node_id = ready.popleft()
            ordered.append(self.nodes[node_id])
            for dependent in outgoing[node_id]:
                incoming[dependent] -= 1
                if incoming[dependent] == 0:
                    ready.append(dependent)

        if len(ordered) != len(self.nodes):
            raise TaskGraphError("Task graph contains a cycle")
        return tuple(ordered)
