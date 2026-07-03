"""Parser plugin contracts and registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from javacvbedrock.errors import PluginRegistrationError
from javacvbedrock.pipeline import ResourceParser


class ParserPlugin(Protocol):
    @property
    def plugin_id(self) -> str: ...

    @property
    def parser(self) -> ResourceParser: ...

    def supports(self, discovered_families: frozenset[str]) -> bool: ...


@dataclass(slots=True)
class ParserRegistry:
    _plugins: dict[str, ParserPlugin]

    @classmethod
    def empty(cls) -> "ParserRegistry":
        return cls({})

    def register(self, plugin: ParserPlugin) -> None:
        if plugin.plugin_id in self._plugins:
            raise PluginRegistrationError(f"Parser plugin already registered: {plugin.plugin_id}")
        self._plugins[plugin.plugin_id] = plugin

    def select(self, discovered_families: frozenset[str]) -> tuple[ParserPlugin, ...]:
        return tuple(plugin for plugin in self._plugins.values() if plugin.supports(discovered_families))
