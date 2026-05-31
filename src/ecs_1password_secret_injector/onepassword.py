"""1Password Connect client wrapper."""

from __future__ import annotations

from typing import Any

import onepasswordconnectsdk

from .config import OnePasswordConfig, SecretMapping
from .exceptions import OnePasswordError, SecretNotFoundError


class OnePasswordClient:
    """Fetches secrets from a 1Password Connect server."""

    def __init__(self, config: OnePasswordConfig) -> None:
        self._config = config
        try:
            self._client = onepasswordconnectsdk.new_client(
                config.connect_url,
                config.token,
            )
        except Exception as exc:
            raise OnePasswordError(
                f"Failed to initialise 1Password Connect client: {exc}"
            ) from exc

    def _get_vault_id(self) -> str:
        """Return the UUID of the configured vault."""
        try:
            vaults = self._client.get_vaults()
        except Exception as exc:
            raise OnePasswordError(f"Failed to retrieve vaults: {exc}") from exc

        for vault in vaults:
            if vault.name == self._config.vault_name:
                return vault.id

        raise OnePasswordError(
            f"Vault '{self._config.vault_name}' not found in 1Password Connect"
        )

    def _get_item(self, vault_id: str, item_title: str) -> Any:
        """Return the item with *item_title* from *vault_id*, or raise SecretNotFoundError."""
        try:
            items = self._client.get_items(vault_id)
        except Exception as exc:
            raise OnePasswordError(
                f"Failed to list items in vault '{self._config.vault_name}': {exc}"
            ) from exc

        for item in items:
            if item.title == item_title:
                return item

        raise SecretNotFoundError(item_title, self._config.vault_name)

    def get_secret(self, mapping: SecretMapping) -> str:
        """Return the plaintext value of the field described by *mapping*."""
        vault_id = self._get_vault_id()
        item = self._get_item(vault_id, mapping.item)

        for f in item.fields or []:
            if f.label == mapping.field:
                return f.value or ""

        raise SecretNotFoundError(mapping.item, self._config.vault_name)

    def get_secrets(self, mappings: list[SecretMapping]) -> dict[str, str]:
        """Return ``{env_var: secret_value}`` for every entry in *mappings*."""
        return {m.env_var: self.get_secret(m) for m in mappings}
