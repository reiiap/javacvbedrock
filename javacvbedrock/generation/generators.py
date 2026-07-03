"""Bedrock output generator contracts.

Generators consume IR only. They may know how to emit Bedrock files, but they
must not depend on parser plugins or source-pack-specific structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from javacvbedrock.diagnostics import ConversionLog
from javacvbedrock.ir import ResourceKind, ResourceStore


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    relative_path: Path
    content: bytes


@dataclass(frozen=True, slots=True)
class GenerationResult:
    files: tuple[GeneratedFile, ...]
    log: ConversionLog


class OutputGenerator(Protocol):
    @property
    def resource_kind(self) -> ResourceKind: ...

    def generate(self, store: ResourceStore) -> GenerationResult: ...
