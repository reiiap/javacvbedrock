"""Project-specific exception hierarchy for architecture/configuration failures."""

from __future__ import annotations


class JavaCVBedrockError(Exception):
    """Base class for project-specific non-conversion exceptions."""


class PluginRegistrationError(JavaCVBedrockError):
    """Raised when parser plugin registration is invalid."""


class TaskGraphError(JavaCVBedrockError):
    """Raised when a task graph cannot be planned or executed safely."""
