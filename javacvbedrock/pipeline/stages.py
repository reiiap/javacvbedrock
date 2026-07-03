"""Single-responsibility pipeline stage contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from javacvbedrock.diagnostics import ConversionLog
from javacvbedrock.ir import Resource, ResourceStore


@dataclass(frozen=True, slots=True)
class StageResult[T]:
    value: T
    log: ConversionLog


@dataclass(frozen=True, slots=True)
class DiscoveredResource:
    path: Path
    family: str
    namespace: str | None = None


@dataclass(frozen=True, slots=True)
class LoadedResource:
    discovered: DiscoveredResource
    content: bytes


class ResourceDiscovery(Protocol):
    def discover(self, root: Path) -> StageResult[tuple[DiscoveredResource, ...]]: ...


class ResourceLoader(Protocol):
    def load(self, resources: tuple[DiscoveredResource, ...]) -> StageResult[tuple[LoadedResource, ...]]: ...


class ResourceParser(Protocol):
    def parse(self, resources: tuple[LoadedResource, ...]) -> StageResult[tuple[Resource, ...]]: ...


class ResourceValidator(Protocol):
    def validate(self, store: ResourceStore) -> ConversionLog: ...


class ResourceTransformer(Protocol):
    def transform(self, store: ResourceStore) -> StageResult[ResourceStore]: ...


class ResourceOptimizer(Protocol):
    def optimize(self, store: ResourceStore) -> StageResult[ResourceStore]: ...


class Packager(Protocol):
    def package(self, generated_root: Path, output_path: Path) -> ConversionLog: ...
