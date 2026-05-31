"""Tests for exception types and hierarchy."""

from __future__ import annotations

import pytest

from ecs_1password_secret_injector.exceptions import (
    ConfigurationError,
    ECSError,
    InjectorError,
    OnePasswordError,
    SecretNotFoundError,
)


def test_configuration_error_is_injector_error():
    assert issubclass(ConfigurationError, InjectorError)


def test_onepassword_error_is_injector_error():
    assert issubclass(OnePasswordError, InjectorError)


def test_ecs_error_is_injector_error():
    assert issubclass(ECSError, InjectorError)


def test_secret_not_found_is_onepassword_error():
    assert issubclass(SecretNotFoundError, OnePasswordError)


def test_secret_not_found_message_contains_item_and_vault():
    exc = SecretNotFoundError("my-item", "my-vault")
    assert "my-item" in str(exc)
    assert "my-vault" in str(exc)


def test_secret_not_found_stores_attributes():
    exc = SecretNotFoundError("api-key", "production")
    assert exc.item == "api-key"
    assert exc.vault == "production"


def test_all_leaf_exceptions_catchable_as_injector_error():
    leaf_instances = [
        ConfigurationError("test"),
        OnePasswordError("test"),
        SecretNotFoundError("item", "vault"),
        ECSError("test"),
    ]
    for exc in leaf_instances:
        with pytest.raises(InjectorError):
            raise exc
