"""Resource pack detection, discovery, indexing, and validation."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path, PurePosixPath

from javacvbedrock.diagnostics import ConversionLog, Diagnostic, Severity
from javacvbedrock.loading.cache import ResourceContentCache
from javacvbedrock.loading.filesystem import PackSource, open_pack_source
from javacvbedrock.loading.index import ResourceIndex
from javacvbedrock.loading.types import (
    PackIdentity,
    PackKind,
    ResourceEntry,
    ResourceType,
    SourceFile,
)

_INVALID_PATH_PATTERN = re.compile(r"(^|/)\.\.(/|$)|\\|\x00")
_INVALID_FILENAME_PATTERN = re.compile(r"[A-Z\s]")
_EXTENSION_TO_TYPE = {
    ".png": ResourceType.PNG,
    ".json": ResourceType.JSON,
    ".mcmeta": ResourceType.MCMETA,
    ".lang": ResourceType.LANG,
    ".ogg": ResourceType.OGG,
    ".fsh": ResourceType.FSH,
    ".vsh": ResourceType.VSH,
    ".txt": ResourceType.TXT,
    ".yaml": ResourceType.YAML,
    ".yml": ResourceType.YML,
    ".properties": ResourceType.PROPERTIES,
}
_KNOWN_RESOURCE_DIRS = frozenset(
    {
        "textures",
        "models",
        "font",
        "sounds",
        "particles",
        "lang",
        "atlases",
        "animations",
        "animation_controllers",
        "items",
        "blocks",
        "optifine",
        "cit",
        "emissive",
    }
)


class ResourcePackLoader:
    def load(self, input_path: Path) -> ResourceIndex:
        source = open_pack_source(input_path)
        return ResourceDiscoveryEngine().discover(source)


class ResourceDiscoveryEngine:
    def discover(self, source: PackSource) -> ResourceIndex:
        log = ConversionLog().add(
            Diagnostic(Severity.INFO, "loader.open", f"Loading {source.name} from {source.root_uri}.")
        )
        source_files = source.list_files()
        file_entries = tuple(entry for entry in source_files if not entry.is_directory)
        directories = tuple(entry.relative_path for entry in source_files if entry.is_directory)
        empty_folders = self._find_empty_folders(directories, file_entries)
        namespaces = self._discover_namespaces(file_entries)
        kind = self._detect_pack_kind(file_entries)
        identity = PackIdentity(name=source.name, kind=kind, root=source.root_uri)
        cache = ResourceContentCache(source)

        for namespace in sorted(namespaces):
            log = log.add(Diagnostic(Severity.INFO, "loader.namespace", f"Scanning namespace '{namespace}'."))

        entries: list[ResourceEntry] = []
        for source_file in file_entries:
            content = cache.read(source_file.relative_path)
            entries.append(self._entry_for(source, identity, source_file, content))

        log = self._add_discovery_counts(log, entries)
        log = self._validate(log, file_entries, entries, empty_folders)
        log = log.add(Diagnostic(Severity.INFO, "loader.indexed", f"Indexed {len(entries):,} files."))
        log = log.add(Diagnostic(Severity.INFO, "loader.validation.complete", "Validation complete."))
        return ResourceIndex(
            origin_pack=identity,
            entries=tuple(entries),
            namespaces=frozenset(namespaces),
            empty_folders=empty_folders,
            log=log,
            _cache=cache,
        )

    def _entry_for(
        self,
        source: PackSource,
        identity: PackIdentity,
        source_file: SourceFile,
        content: bytes,
    ) -> ResourceEntry:
        extension = source_file.relative_path.suffix.lower()
        resource_type = _EXTENSION_TO_TYPE.get(extension, ResourceType.UNKNOWN)
        namespace = self._namespace_for(source_file.relative_path)
        resource_id = self._resource_id(namespace, source_file.relative_path)
        return ResourceEntry(
            id=resource_id,
            namespace=namespace,
            relative_path=source_file.relative_path,
            absolute_path=source.absolute_path(source_file.relative_path),
            resource_type=resource_type,
            file_extension=extension.removeprefix("."),
            file_size=source_file.size,
            sha256=hashlib.sha256(content).hexdigest(),
            last_modified=source_file.last_modified,
            origin_pack=identity,
            metadata={"resource_family": self._resource_family(source_file.relative_path)},
        )

    def _detect_pack_kind(self, files: tuple[SourceFile, ...]) -> PackKind:
        paths = frozenset(file.relative_path.as_posix().lower() for file in files)
        if any(path.startswith("contents/") and "itemsadder" in path for path in paths) or any(
            path.endswith("itemsadder.yml") or path.endswith("itemsadder.yaml") for path in paths
        ):
            return PackKind.ITEMSADDER
        if any(path.endswith("nexo.yml") or path.endswith("nexo.yaml") for path in paths) or any(
            "/nexo/" in f"/{path}/" for path in paths
        ):
            return PackKind.NEXO
        if any(path.endswith("oraxen.yml") or path.endswith("oraxen.yaml") for path in paths) or any(
            "/oraxen/" in f"/{path}/" for path in paths
        ):
            return PackKind.ORAXEN
        if "pack.mcmeta" in paths and any(path.startswith("assets/") for path in paths):
            return PackKind.VANILLA
        return PackKind.UNKNOWN

    def _discover_namespaces(self, files: tuple[SourceFile, ...]) -> set[str]:
        namespaces: set[str] = set()
        for file in files:
            parts = file.relative_path.parts
            if len(parts) >= 2 and parts[0] == "assets":
                namespaces.add(parts[1])
        return namespaces

    def _namespace_for(self, path: PurePosixPath) -> str | None:
        parts = path.parts
        if len(parts) >= 2 and parts[0] == "assets":
            return parts[1]
        return None

    def _resource_id(self, namespace: str | None, path: PurePosixPath) -> str:
        if namespace is None:
            return path.as_posix()
        parts = path.parts
        if len(parts) > 2:
            return f"{namespace}:{PurePosixPath(*parts[2:]).as_posix()}"
        return f"{namespace}:"

    def _resource_family(self, path: PurePosixPath) -> str:
        parts = path.parts
        if len(parts) >= 3 and parts[0] == "assets":
            return parts[2]
        if len(parts) >= 1:
            return parts[0]
        return "unknown"

    def _find_empty_folders(
        self,
        directories: tuple[PurePosixPath, ...],
        files: tuple[SourceFile, ...],
    ) -> tuple[PurePosixPath, ...]:
        file_paths = tuple(file.relative_path.as_posix() for file in files)
        empty = []
        for directory in directories:
            prefix = directory.as_posix().rstrip("/") + "/"
            if not any(path.startswith(prefix) for path in file_paths):
                empty.append(directory)
        return tuple(empty)

    def _add_discovery_counts(self, log: ConversionLog, entries: list[ResourceEntry]) -> ConversionLog:
        family_counts = Counter(str(entry.metadata.get("resource_family", "unknown")) for entry in entries)
        for family in sorted(_KNOWN_RESOURCE_DIRS):
            count = family_counts.get(family, 0)
            if count:
                log = log.add(
                    Diagnostic(
                        Severity.INFO,
                        f"loader.discovered.{family}",
                        f"Discovered {count:,} {family}.",
                    )
                )
        unknown_custom = sum(1 for entry in entries if entry.metadata.get("resource_family") not in _KNOWN_RESOURCE_DIRS)
        if unknown_custom:
            log = log.add(
                Diagnostic(
                    Severity.INFO,
                    "loader.discovered.custom",
                    f"Discovered {unknown_custom:,} custom or root files.",
                )
            )
        return log

    def _validate(
        self,
        log: ConversionLog,
        files: tuple[SourceFile, ...],
        entries: list[ResourceEntry],
        empty_folders: tuple[PurePosixPath, ...],
    ) -> ConversionLog:
        paths = [file.relative_path.as_posix() for file in files]
        lower_paths = Counter(path.lower() for path in paths)
        if "pack.mcmeta" not in {path.lower() for path in paths}:
            log = log.add(Diagnostic(Severity.WARNING, "pack.mcmeta.missing", "Missing pack.mcmeta."))
        if not any(path.lower().startswith("assets/") for path in paths):
            log = log.add(Diagnostic(Severity.WARNING, "assets.missing", "Missing assets folder."))
        for path, count in lower_paths.items():
            if count > 1:
                log = log.add(
                    Diagnostic(
                        Severity.RECOVERABLE_ERROR,
                        "path.duplicate",
                        f"Duplicate resource path '{path}' appears {count} times.",
                    )
                )
        for entry in entries:
            path = entry.relative_path.as_posix()
            if _INVALID_PATH_PATTERN.search(path):
                log = log.add(
                    Diagnostic(
                        Severity.WARNING,
                        "path.broken",
                        f"Broken resource path: {path}",
                        resource=entry.id,
                    )
                )
            if _INVALID_FILENAME_PATTERN.search(path):
                log = log.add(
                    Diagnostic(
                        Severity.WARNING,
                        "path.invalid_filename",
                        f"Invalid filename for Minecraft resource: {path}",
                        resource=entry.id,
                    )
                )
            if entry.resource_type == ResourceType.UNKNOWN:
                log = log.add(
                    Diagnostic(
                        Severity.WARNING,
                        "file.unsupported_type",
                        f"Unsupported or unknown file type: {path}",
                        resource=entry.id,
                    )
                )
        for folder in empty_folders:
            log = log.add(
                Diagnostic(Severity.WARNING, "folder.empty", f"Empty folder discovered: {folder.as_posix()}")
            )
        return log
