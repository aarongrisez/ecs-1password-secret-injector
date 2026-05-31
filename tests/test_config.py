"""Tests for configuration loading and validation."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from ecs_1password_secret_injector.config import (
    ECSConfig,
    InjectorConfig,
    OnePasswordConfig,
    SecretMapping,
)
from ecs_1password_secret_injector.exceptions import ConfigurationError

_VALID_ENV = {
    "OP_CONNECT_URL": "https://op.example.com",
    "OP_CONNECT_TOKEN": "token123",
    "OP_VAULT_NAME": "Production",
    "AWS_REGION": "us-east-1",
    "ECS_CLUSTER": "my-cluster",
    "ECS_SERVICE": "my-service",
    "ECS_TASK_DEFINITION": "my-task",
    "SECRET_MAPPINGS": json.dumps(
        [{"item": "api-key", "field": "credential", "env_var": "API_KEY"}]
    ),
}


def test_from_env_returns_correct_config():
    with patch.dict(os.environ, _VALID_ENV, clear=True):
        config = InjectorConfig.from_env()

    assert config.onepassword.connect_url == "https://op.example.com"
    assert config.onepassword.token == "token123"
    assert config.onepassword.vault_name == "Production"
    assert config.ecs.region == "us-east-1"
    assert config.ecs.cluster == "my-cluster"
    assert config.ecs.service == "my-service"
    assert config.ecs.task_definition == "my-task"
    assert len(config.secrets) == 1
    assert config.secrets[0].item == "api-key"
    assert config.secrets[0].field == "credential"
    assert config.secrets[0].env_var == "API_KEY"


def test_from_env_multiple_secret_mappings():
    mappings = [
        {"item": "api-key", "field": "credential", "env_var": "API_KEY"},
        {"item": "db", "field": "password", "env_var": "DB_PASS"},
    ]
    env = {**_VALID_ENV, "SECRET_MAPPINGS": json.dumps(mappings)}
    with patch.dict(os.environ, env, clear=True):
        config = InjectorConfig.from_env()

    assert len(config.secrets) == 2
    assert config.secrets[1].item == "db"


@pytest.mark.parametrize("missing_key", list(_VALID_ENV.keys()))
def test_from_env_missing_variable_raises_configuration_error(missing_key):
    env = {k: v for k, v in _VALID_ENV.items() if k != missing_key}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match=missing_key):
            InjectorConfig.from_env()


def test_from_env_invalid_json_raises_configuration_error():
    env = {**_VALID_ENV, "SECRET_MAPPINGS": "not-json"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match="not valid JSON"):
            InjectorConfig.from_env()


def test_from_env_mappings_not_array_raises_configuration_error():
    env = {**_VALID_ENV, "SECRET_MAPPINGS": '{"item": "x"}'}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match="JSON array"):
            InjectorConfig.from_env()


def test_from_env_mapping_missing_field_raises_configuration_error():
    incomplete = [{"item": "x", "field": "y"}]  # missing env_var
    env = {**_VALID_ENV, "SECRET_MAPPINGS": json.dumps(incomplete)}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match="env_var"):
            InjectorConfig.from_env()


def test_secret_mapping_dataclass_stores_fields():
    m = SecretMapping(item="my-item", field="my-field", env_var="MY_VAR")
    assert m.item == "my-item"
    assert m.field == "my-field"
    assert m.env_var == "MY_VAR"


def test_injector_config_default_empty_secrets():
    config = InjectorConfig(
        onepassword=OnePasswordConfig(
            connect_url="https://op.example.com", token="tok", vault_name="vault"
        ),
        ecs=ECSConfig(
            region="us-east-1",
            cluster="c",
            service="s",
            task_definition="td",
        ),
    )
    assert config.secrets == []
