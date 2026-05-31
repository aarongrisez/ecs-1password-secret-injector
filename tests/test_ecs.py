"""Tests for the ECS client wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from ecs_1password_secret_injector.config import ECSConfig
from ecs_1password_secret_injector.ecs import ECSClient
from ecs_1password_secret_injector.exceptions import ECSError

_PATCH_BOTO3 = "ecs_1password_secret_injector.ecs.boto3.client"


def _make_config():
    return ECSConfig(
        region="us-east-1",
        cluster="my-cluster",
        service="my-service",
        task_definition="my-task",
    )


def _client_error(code="ClientException", message="error"):
    return botocore.exceptions.ClientError(
        {"Error": {"Code": code, "Message": message}},
        "Operation",
    )


def _make_task_def(**overrides):
    base = {
        "family": "my-task",
        "containerDefinitions": [
            {
                "name": "app",
                "image": "my-image:latest",
                "environment": [{"name": "EXISTING_VAR", "value": "existing"}],
            }
        ],
        # Read-only fields that must be stripped before re-registering:
        "taskDefinitionArn": "arn:aws:ecs:us-east-1:123:task-definition/my-task:1",
        "revision": 1,
        "status": "ACTIVE",
        "requiresAttributes": [],
        "compatibilities": ["EC2"],
        "registeredAt": "2024-01-01T00:00:00Z",
        "registeredBy": "arn:aws:iam::123:user/user",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# get_current_task_definition
# ---------------------------------------------------------------------------


def test_get_current_task_definition_returns_task_def():
    mock_boto = MagicMock()
    mock_boto.describe_task_definition.return_value = {"taskDefinition": _make_task_def()}

    with patch(_PATCH_BOTO3, return_value=mock_boto):
        client = ECSClient(_make_config())
        td = client.get_current_task_definition()

    assert td["family"] == "my-task"
    mock_boto.describe_task_definition.assert_called_once_with(taskDefinition="my-task")


def test_get_current_task_definition_raises_ecs_error_on_client_error():
    mock_boto = MagicMock()
    mock_boto.describe_task_definition.side_effect = _client_error(message="not found")

    with patch(_PATCH_BOTO3, return_value=mock_boto):
        client = ECSClient(_make_config())
        with pytest.raises(ECSError, match="my-task"):
            client.get_current_task_definition()


# ---------------------------------------------------------------------------
# register_task_definition_with_env
# ---------------------------------------------------------------------------


def test_register_merges_new_env_vars_into_containers():
    mock_boto = MagicMock()
    mock_boto.describe_task_definition.return_value = {"taskDefinition": _make_task_def()}
    mock_boto.register_task_definition.return_value = {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123:task-definition/my-task:2"
        }
    }

    with patch(_PATCH_BOTO3, return_value=mock_boto):
        client = ECSClient(_make_config())
        arn = client.register_task_definition_with_env({"NEW_VAR": "new-value"})

    assert arn == "arn:aws:ecs:us-east-1:123:task-definition/my-task:2"

    call_kwargs = mock_boto.register_task_definition.call_args[1]
    env_map = {
        e["name"]: e["value"]
        for e in call_kwargs["containerDefinitions"][0]["environment"]
    }
    assert env_map["EXISTING_VAR"] == "existing"
    assert env_map["NEW_VAR"] == "new-value"


def test_register_new_env_var_overwrites_existing_on_collision():
    task_def = _make_task_def()
    task_def["containerDefinitions"][0]["environment"] = [
        {"name": "SHARED_VAR", "value": "old-value"}
    ]

    mock_boto = MagicMock()
    mock_boto.describe_task_definition.return_value = {"taskDefinition": task_def}
    mock_boto.register_task_definition.return_value = {
        "taskDefinition": {"taskDefinitionArn": "arn:..."}
    }

    with patch(_PATCH_BOTO3, return_value=mock_boto):
        client = ECSClient(_make_config())
        client.register_task_definition_with_env({"SHARED_VAR": "new-value"})

    call_kwargs = mock_boto.register_task_definition.call_args[1]
    env_map = {
        e["name"]: e["value"]
        for e in call_kwargs["containerDefinitions"][0]["environment"]
    }
    assert env_map["SHARED_VAR"] == "new-value"


def test_register_strips_readonly_fields():
    mock_boto = MagicMock()
    mock_boto.describe_task_definition.return_value = {"taskDefinition": _make_task_def()}
    mock_boto.register_task_definition.return_value = {
        "taskDefinition": {"taskDefinitionArn": "arn:..."}
    }

    with patch(_PATCH_BOTO3, return_value=mock_boto):
        client = ECSClient(_make_config())
        client.register_task_definition_with_env({})

    call_kwargs = mock_boto.register_task_definition.call_args[1]
    for readonly_key in (
        "taskDefinitionArn",
        "revision",
        "status",
        "requiresAttributes",
        "compatibilities",
        "registeredAt",
        "registeredBy",
    ):
        assert readonly_key not in call_kwargs, f"'{readonly_key}' should be stripped"


def test_register_raises_ecs_error_on_registration_failure():
    mock_boto = MagicMock()
    mock_boto.describe_task_definition.return_value = {"taskDefinition": _make_task_def()}
    mock_boto.register_task_definition.side_effect = _client_error(message="quota exceeded")

    with patch(_PATCH_BOTO3, return_value=mock_boto):
        client = ECSClient(_make_config())
        with pytest.raises(ECSError, match="revision"):
            client.register_task_definition_with_env({"VAR": "val"})


def test_register_injects_into_all_containers():
    task_def = _make_task_def()
    task_def["containerDefinitions"] = [
        {"name": "app", "image": "app:latest", "environment": []},
        {"name": "sidecar", "image": "sidecar:latest", "environment": []},
    ]

    mock_boto = MagicMock()
    mock_boto.describe_task_definition.return_value = {"taskDefinition": task_def}
    mock_boto.register_task_definition.return_value = {
        "taskDefinition": {"taskDefinitionArn": "arn:..."}
    }

    with patch(_PATCH_BOTO3, return_value=mock_boto):
        client = ECSClient(_make_config())
        client.register_task_definition_with_env({"MY_VAR": "val"})

    call_kwargs = mock_boto.register_task_definition.call_args[1]
    for container in call_kwargs["containerDefinitions"]:
        env_names = [e["name"] for e in container["environment"]]
        assert "MY_VAR" in env_names, f"MY_VAR missing from container '{container['name']}'"
