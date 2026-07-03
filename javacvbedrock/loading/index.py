"""Indexed resource database produced by the loading pipeline."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath

from javacvbedrock.diagnostics import ConversionLog, Diagnostic, Severity
from javacvbedrock.loading.cache import ResourceContentCache
from javacvbedrock.loading.types import PackIdentity, ResourceEntry, ResourceType


@dataclass(frozen=True, slots=True)
class ResourceIndex:
    origin_pack: PackIdentity
    entries: tuple[ResourceEntry, ...]
    namespaces: frozenset[str]
    empty_folders: tuple[PurePosixPath, ...]
    log: ConversionLog
    _cache: ResourceContentCache

    def read(self, entry: ResourceEntry) -> bytes:
        return self._cache.read(entry.relative_path)

    def by_namespace(self, namespace: str) -> tuple[ResourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.namespace == namespace)

    def by_type(self, resource_type: ResourceType) -> tuple[ResourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.resource_type == resource_type)

    def validation_log(self) -> ConversionLog:
        log = self.log
        ids = Counter(entry.id for entry in self.entries)
        for duplicate_id, count in ids.items():
            if count > 1:
                log = log.add(
                    Diagnostic(
                        severity=Severity.RECOVERABLE_ERROR,
                        code="resource.duplicate",
                        message=f"Duplicate resource id '{duplicate_id}' appears {count} times.",
                        resource=duplicate_id,
                    )
                )
        return log
