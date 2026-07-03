"""Structured diagnostics for conversion runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class Severity(StrEnum):
    WARNING = "warning"
    RECOVERABLE_ERROR = "recoverable_error"
    FATAL_ERROR = "fatal_error"
    UNSUPPORTED_FEATURE = "unsupported_feature"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    resource: str | None = None
    source_path: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConversionLog:
    diagnostics: tuple[Diagnostic, ...] = ()

    def add(self, diagnostic: Diagnostic) -> "ConversionLog":
        return ConversionLog((*self.diagnostics, diagnostic))

    def has_fatal_errors(self) -> bool:
        return any(item.severity == Severity.FATAL_ERROR for item in self.diagnostics)

    def by_severity(self, severity: Severity) -> tuple[Diagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == severity)
