"""Immutable IR resource collection primitives."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from javacvbedrock.ir.resources import Resource, ResourceId, ResourceKind


@dataclass(frozen=True, slots=True)
class ResourceStore:
    _resources: Mapping[str, Resource]

    @classmethod
    def empty(cls) -> "ResourceStore":
        return cls(MappingProxyType({}))

    @classmethod
    def from_resources(cls, resources: Iterable[Resource]) -> "ResourceStore":
        return cls(MappingProxyType({resource.id.as_key(): resource for resource in resources}))

    def get(self, resource_id: ResourceId) -> Resource | None:
        return self._resources.get(resource_id.as_key())

    def by_kind(self, kind: ResourceKind) -> tuple[Resource, ...]:
        return tuple(resource for resource in self._resources.values() if resource.kind == kind)

    def all(self) -> tuple[Resource, ...]:
        return tuple(self._resources.values())
