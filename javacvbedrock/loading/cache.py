"""Lazy read-through resource byte cache."""

from __future__ import annotations

from pathlib import PurePosixPath
from threading import Lock

from javacvbedrock.loading.filesystem import PackSource


class ResourceContentCache:
    def __init__(self, source: PackSource) -> None:
        self._source = source
        self._cache: dict[str, bytes] = {}
        self._lock = Lock()

    def read(self, relative_path: PurePosixPath) -> bytes:
        key = relative_path.as_posix()
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            content = self._source.read_bytes(relative_path)
            self._cache[key] = content
            return content

    def cached_count(self) -> int:
        with self._lock:
            return len(self._cache)
