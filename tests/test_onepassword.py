"""Tests for the 1Password Connect client wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ecs_1password_secret_injector.config import OnePasswordConfig, SecretMapping
from ecs_1password_secret_injector.exceptions import OnePasswordError, SecretNotFoundError
from ecs_1password_secret_injector.onepassword import OnePasswordClient

_PATCH_NEW_CLIENT = "ecs_1password_secret_injector.onepassword.onepasswordconnectsdk.new_client"


def _make_config():
    return OnePasswordConfig(
        connect_url="https://op.example.com",
        token="tok",
        vault_name="Production",
    )


def _make_mapping(item="api-key", field="credential", env_var="API_KEY"):
    return SecretMapping(item=item, field=field, env_var=env_var)


def _mock_vault(vault_id="vault-id", name="Production"):
    v = MagicMock()
    v.id = vault_id
    v.name = name
    return v


def _mock_item(title, fields):
    item = MagicMock()
    item.title = title
    item.fields = fields
    return item


def _mock_field(label, value):
    f = MagicMock()
    f.label = label
    f.value = value
    return f


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_init_raises_onepassword_error_on_client_failure():
    with patch(_PATCH_NEW_CLIENT, side_effect=Exception("connection refused")):
        with pytest.raises(OnePasswordError, match="connection refused"):
            OnePasswordClient(_make_config())


# ---------------------------------------------------------------------------
# get_secret — happy path
# ---------------------------------------------------------------------------


def test_get_secret_returns_field_value():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault()]
    mock_client.get_items.return_value = [
        _mock_item("api-key", [_mock_field("credential", "super-secret")])
    ]

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        result = client.get_secret(_make_mapping())

    assert result == "super-secret"
    mock_client.get_vaults.assert_called_once()
    mock_client.get_items.assert_called_once_with("vault-id")


def test_get_secret_returns_empty_string_for_null_field_value():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault()]
    mock_client.get_items.return_value = [
        _mock_item("api-key", [_mock_field("credential", None)])
    ]

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        result = client.get_secret(_make_mapping())

    assert result == ""


# ---------------------------------------------------------------------------
# get_secret — error paths
# ---------------------------------------------------------------------------


def test_get_secret_raises_onepassword_error_on_vault_list_failure():
    mock_client = MagicMock()
    mock_client.get_vaults.side_effect = Exception("network timeout")

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        with pytest.raises(OnePasswordError, match="network timeout"):
            client.get_secret(_make_mapping())


def test_get_secret_raises_onepassword_error_when_vault_not_found():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault(name="OtherVault")]

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        with pytest.raises(OnePasswordError, match="Production"):
            client.get_secret(_make_mapping())


def test_get_secret_raises_onepassword_error_on_item_list_failure():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault()]
    mock_client.get_items.side_effect = Exception("unauthorised")

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        with pytest.raises(OnePasswordError, match="unauthorised"):
            client.get_secret(_make_mapping())


def test_get_secret_raises_secret_not_found_when_item_absent():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault()]
    mock_client.get_items.return_value = []

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        with pytest.raises(SecretNotFoundError):
            client.get_secret(_make_mapping())


def test_get_secret_raises_secret_not_found_when_field_absent():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault()]
    mock_client.get_items.return_value = [
        _mock_item("api-key", [_mock_field("other-field", "value")])
    ]

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        with pytest.raises(SecretNotFoundError):
            client.get_secret(_make_mapping(field="missing-field"))


# ---------------------------------------------------------------------------
# get_secrets
# ---------------------------------------------------------------------------


def test_get_secrets_returns_all_mappings():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault()]

    items_by_title = {
        "api-key": _mock_item("api-key", [_mock_field("credential", "secret1")]),
        "db-pass": _mock_item("db-pass", [_mock_field("password", "secret2")]),
    }
    mock_client.get_items.return_value = list(items_by_title.values())

    mappings = [
        _make_mapping(item="api-key", field="credential", env_var="API_KEY"),
        _make_mapping(item="db-pass", field="password", env_var="DB_PASS"),
    ]

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        result = client.get_secrets(mappings)

    assert result == {"API_KEY": "secret1", "DB_PASS": "secret2"}


def test_get_secrets_empty_mappings_returns_empty_dict():
    mock_client = MagicMock()
    mock_client.get_vaults.return_value = [_mock_vault()]
    mock_client.get_items.return_value = []

    with patch(_PATCH_NEW_CLIENT, return_value=mock_client):
        client = OnePasswordClient(_make_config())
        result = client.get_secrets([])

    assert result == {}
