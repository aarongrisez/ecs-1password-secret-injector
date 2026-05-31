"""Custom exception types for the ECS 1Password secret injector."""

from __future__ import annotations


class InjectorError(Exception):
    """Base exception for all injector errors."""


class ConfigurationError(InjectorError):
    """Raised when required configuration is missing or invalid."""


class OnePasswordError(InjectorError):
    """Raised when a 1Password Connect operation fails."""


class SecretNotFoundError(OnePasswordError):
    """Raised when a requested item or field cannot be found in 1Password."""

    def __init__(self, item: str, vault: str) -> None:
        self.item = item
        self.vault = vault
        super().__init__(f"Secret '{item}' not found in vault '{vault}'")


class ECSError(InjectorError):
    """Raised when an AWS ECS operation fails."""
