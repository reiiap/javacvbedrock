"""Filesystem abstraction used by pack discovery.

Parsers should consume ResourceIndex entries and this source abstraction instead
of directly opening local files or archive members.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from javacvbedrock.errors import JavaCVBedrockError
from javacvbedrock.loading.types import SourceFile, SUPPORTED_ARCHIVE_EXTENSIONS


class PackSourceError(JavaCVBedrockError):
    """Raised when an input pack source cannot be opened."""


class PackSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def root_uri(self) -> str: ...

    @abstractmethod
    def list_files(self) -> tuple[SourceFile, ...]: ...

    @abstractmethod
    def read_bytes(self, relative_path: PurePosixPath) -> bytes: ...

    @abstractmethod
    def absolute_path(self, relative_path: PurePosixPath) -> str: ...


class LocalFolderSource(PackSource):
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        if not self._root.is_dir():
            raise PackSourceError(f"Pack folder does not exist: {root}")

    @property
    def name(self) -> str:
        return self._root.name

    @property
    def root_uri(self) -> str:
        return self._root.as_uri()

    def list_files(self) -> tuple[SourceFile, ...]:
        entries: list[SourceFile] = []
        for path in self._root.rglob("*"):
            relative = PurePosixPath(path.relative_to(self._root).as_posix())
            stat = path.stat()
            entries.append(
                SourceFile(
                    relative_path=relative,
                    size=0 if path.is_dir() else stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                    is_directory=path.is_dir(),
                )
            )
        return tuple(sorted(entries, key=lambda item: item.relative_path.as_posix()))

    def read_bytes(self, relative_path: PurePosixPath) -> bytes:
        path = (self._root / Path(relative_path.as_posix())).resolve()
        if not path.is_relative_to(self._root) or not path.is_file():
            raise PackSourceError(f"Resource is outside pack root or is not a file: {relative_path}")
        return path.read_bytes()

    def absolute_path(self, relative_path: PurePosixPath) -> str:
        return str((self._root / Path(relative_path.as_posix())).resolve())


class ZipArchiveSource(PackSource):
    def __init__(self, archive: Path) -> None:
        self._archive = archive.resolve()
        if self._archive.suffix.lower() not in SUPPORTED_ARCHIVE_EXTENSIONS:
            raise PackSourceError(f"Unsupported archive extension: {archive.suffix}")
        if not self._archive.is_file():
            raise PackSourceError(f"Pack archive does not exist: {archive}")
        try:
            with ZipFile(self._archive):
                pass
        except BadZipFile as exc:
            raise PackSourceError(f"Pack archive is not a valid ZIP-compatible file: {archive}") from exc

    @property
    def name(self) -> str:
        return self._archive.stem

    @property
    def root_uri(self) -> str:
        return self._archive.as_uri()

    def list_files(self) -> tuple[SourceFile, ...]:
        entries: list[SourceFile] = []
        with ZipFile(self._archive) as archive:
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                if path.as_posix() == ".":
                    continue
                entries.append(
                    SourceFile(
                        relative_path=path,
                        size=0 if info.is_dir() else info.file_size,
                        last_modified=datetime(*info.date_time, tzinfo=timezone.utc),
                        is_directory=info.is_dir(),
                    )
                )
        return tuple(entries)

    def read_bytes(self, relative_path: PurePosixPath) -> bytes:
        with ZipFile(self._archive) as archive:
            return archive.read(relative_path.as_posix())

    def absolute_path(self, relative_path: PurePosixPath) -> str:
        return f"{self._archive}!/{relative_path.as_posix()}"


def open_pack_source(path: Path) -> PackSource:
    if path.is_dir():
        return LocalFolderSource(path)
    if path.suffix.lower() in SUPPORTED_ARCHIVE_EXTENSIONS:
        return ZipArchiveSource(path)
    raise PackSourceError(f"Unsupported pack input: {path}")
