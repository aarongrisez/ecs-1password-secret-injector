"""ECS 1Password Secret Injector.

Provides :class:`SecretInjector` as the primary public interface.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .config import ECSConfig, InjectorConfig, OnePasswordConfig, SecretMapping
from .exceptions import (
    ConfigurationError,
    ECSError,
    InjectorError,
    OnePasswordError,
    SecretNotFoundError,
)
from .injector import SecretInjector

__all__ = [
    "SecretInjector",
    "InjectorConfig",
    "OnePasswordConfig",
    "ECSConfig",
    "SecretMapping",
    "InjectorError",
    "ConfigurationError",
    "OnePasswordError",
    "SecretNotFoundError",
    "ECSError",
]
