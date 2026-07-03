"""Resource loading domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Mapping


class PackKind(StrEnum):
    VANILLA = "vanilla"
    ITEMSADDER = "itemsadder"
    NEXO = "nexo"
    ORAXEN = "oraxen"
    UNKNOWN = "unknown"


class ResourceType(StrEnum):
    PNG = "png"
    JSON = "json"
    MCMETA = "mcmeta"
    LANG = "lang"
    OGG = "ogg"
    FSH = "fsh"
    VSH = "vsh"
    TXT = "txt"
    YAML = "yaml"
    YML = "yml"
    PROPERTIES = "properties"
    UNKNOWN = "unknown"


SUPPORTED_ARCHIVE_EXTENSIONS = frozenset({".zip", ".mcpack", ".mcaddon"})


@dataclass(frozen=True, slots=True)
class PackIdentity:
    name: str
    kind: PackKind
    root: str


@dataclass(frozen=True, slots=True)
class SourceFile:
    relative_path: PurePosixPath
    size: int
    last_modified: datetime
    is_directory: bool = False

    def __post_init__(self) -> None:
        if self.last_modified.tzinfo is None:
            object.__setattr__(self, "last_modified", self.last_modified.replace(tzinfo=timezone.utc))


@dataclass(frozen=True, slots=True)
class ResourceEntry:
    id: str
    namespace: str | None
    relative_path: PurePosixPath
    absolute_path: str
    resource_type: ResourceType
    file_extension: str
    file_size: int
    sha256: str
    last_modified: datetime
    origin_pack: PackIdentity
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
