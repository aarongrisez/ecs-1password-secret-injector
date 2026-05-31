"""Tests for the top-level SecretInjector orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ecs_1password_secret_injector.config import (
    ECSConfig,
    InjectorConfig,
    OnePasswordConfig,
    SecretMapping,
)
from ecs_1password_secret_injector.exceptions import ECSError, OnePasswordError
from ecs_1password_secret_injector.injector import SecretInjector

_PATCH_OP = "ecs_1password_secret_injector.injector.OnePasswordClient"
_PATCH_ECS = "ecs_1password_secret_injector.injector.ECSClient"


def _make_config(mappings=None):
    return InjectorConfig(
        onepassword=OnePasswordConfig(
            connect_url="https://op.example.com",
            token="tok",
            vault_name="Production",
        ),
        ecs=ECSConfig(
            region="us-east-1",
            cluster="my-cluster",
            service="my-service",
            task_definition="my-task",
        ),
        secrets=mappings
        or [SecretMapping(item="api-key", field="credential", env_var="API_KEY")],
    )


# ---------------------------------------------------------------------------
# inject — happy path
# ---------------------------------------------------------------------------


def test_inject_returns_new_task_definition_arn():
    mock_op_instance = MagicMock()
    mock_op_instance.get_secrets.return_value = {"API_KEY": "super-secret"}

    mock_ecs_instance = MagicMock()
    mock_ecs_instance.register_task_definition_with_env.return_value = (
        "arn:aws:ecs:us-east-1:123:task-definition/my-task:2"
    )

    with patch(_PATCH_OP, return_value=mock_op_instance), \
            patch(_PATCH_ECS, return_value=mock_ecs_instance):
        injector = SecretInjector(_make_config())
        arn = injector.inject()

    assert arn == "arn:aws:ecs:us-east-1:123:task-definition/my-task:2"


def test_inject_passes_secrets_to_ecs():
    mock_op_instance = MagicMock()
    mock_op_instance.get_secrets.return_value = {"API_KEY": "secret-val"}

    mock_ecs_instance = MagicMock()
    mock_ecs_instance.register_task_definition_with_env.return_value = "arn:..."

    with patch(_PATCH_OP, return_value=mock_op_instance), \
            patch(_PATCH_ECS, return_value=mock_ecs_instance):
        injector = SecretInjector(_make_config())
        injector.inject()

    mock_op_instance.get_secrets.assert_called_once()
    mock_ecs_instance.register_task_definition_with_env.assert_called_once_with(
        {"API_KEY": "secret-val"}
    )


def test_inject_calls_get_secrets_with_config_mappings():
    mappings = [
        SecretMapping(item="api-key", field="credential", env_var="API_KEY"),
        SecretMapping(item="db", field="password", env_var="DB_PASS"),
    ]
    mock_op_instance = MagicMock()
    mock_op_instance.get_secrets.return_value = {
        "API_KEY": "v1",
        "DB_PASS": "v2",
    }
    mock_ecs_instance = MagicMock()
    mock_ecs_instance.register_task_definition_with_env.return_value = "arn:..."

    with patch(_PATCH_OP, return_value=mock_op_instance), \
            patch(_PATCH_ECS, return_value=mock_ecs_instance):
        injector = SecretInjector(_make_config(mappings=mappings))
        injector.inject()

    call_args = mock_op_instance.get_secrets.call_args[0][0]
    assert call_args == mappings


# ---------------------------------------------------------------------------
# inject — error propagation
# ---------------------------------------------------------------------------


def test_inject_propagates_onepassword_error():
    mock_op_instance = MagicMock()
    mock_op_instance.get_secrets.side_effect = OnePasswordError("vault not found")

    mock_ecs_instance = MagicMock()

    with patch(_PATCH_OP, return_value=mock_op_instance), \
            patch(_PATCH_ECS, return_value=mock_ecs_instance):
        injector = SecretInjector(_make_config())
        with pytest.raises(OnePasswordError, match="vault not found"):
            injector.inject()


def test_inject_propagates_ecs_error():
    mock_op_instance = MagicMock()
    mock_op_instance.get_secrets.return_value = {"API_KEY": "val"}

    mock_ecs_instance = MagicMock()
    mock_ecs_instance.register_task_definition_with_env.side_effect = ECSError(
        "quota exceeded"
    )

    with patch(_PATCH_OP, return_value=mock_op_instance), \
            patch(_PATCH_ECS, return_value=mock_ecs_instance):
        injector = SecretInjector(_make_config())
        with pytest.raises(ECSError, match="quota exceeded"):
            injector.inject()


def test_inject_does_not_call_ecs_if_onepassword_fails():
    mock_op_instance = MagicMock()
    mock_op_instance.get_secrets.side_effect = OnePasswordError("unauthorised")

    mock_ecs_instance = MagicMock()

    with patch(_PATCH_OP, return_value=mock_op_instance), \
            patch(_PATCH_ECS, return_value=mock_ecs_instance):
        injector = SecretInjector(_make_config())
        with pytest.raises(OnePasswordError):
            injector.inject()

    mock_ecs_instance.register_task_definition_with_env.assert_not_called()
