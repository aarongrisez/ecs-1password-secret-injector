"""Configuration dataclasses and environment-variable loading."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .exceptions import ConfigurationError


@dataclass
class OnePasswordConfig:
    """Connection settings for a 1Password Connect server."""

    connect_url: str
    token: str
    vault_name: str


@dataclass
class ECSConfig:
    """Target ECS task definition settings."""

    region: str
    cluster: str
    service: str
    task_definition: str


@dataclass
class SecretMapping:
    """Describes one secret to fetch and the environment variable to inject it into."""

    item: str
    field: str
    env_var: str


@dataclass
class InjectorConfig:
    """Top-level configuration for a single injection run."""

    onepassword: OnePasswordConfig
    ecs: ECSConfig
    secrets: list[SecretMapping] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> InjectorConfig:
        """Build an InjectorConfig from environment variables.

        Required variables
        ------------------
        OP_CONNECT_URL
            URL of the 1Password Connect server.
        OP_CONNECT_TOKEN
            API token for the Connect server.
        OP_VAULT_NAME
            Name of the vault to read secrets from.
        AWS_REGION
            AWS region where the ECS cluster is hosted.
        ECS_CLUSTER
            ECS cluster name.
        ECS_SERVICE
            ECS service name.
        ECS_TASK_DEFINITION
            ECS task definition family name.
        SECRET_MAPPINGS
            JSON array of ``{"item", "field", "env_var"}`` objects.
        """

        def require(name: str) -> str:
            value = os.environ.get(name)
            if not value:
                raise ConfigurationError(
                    f"Required environment variable '{name}' is not set"
                )
            return value

        op_config = OnePasswordConfig(
            connect_url=require("OP_CONNECT_URL"),
            token=require("OP_CONNECT_TOKEN"),
            vault_name=require("OP_VAULT_NAME"),
        )
        ecs_config = ECSConfig(
            region=require("AWS_REGION"),
            cluster=require("ECS_CLUSTER"),
            service=require("ECS_SERVICE"),
            task_definition=require("ECS_TASK_DEFINITION"),
        )

        raw_mappings = require("SECRET_MAPPINGS")
        try:
            parsed = json.loads(raw_mappings)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"SECRET_MAPPINGS is not valid JSON: {exc}"
            ) from exc

        if not isinstance(parsed, list):
            raise ConfigurationError("SECRET_MAPPINGS must be a JSON array")

        secrets: list[SecretMapping] = []
        for idx, entry in enumerate(parsed):
            for key in ("item", "field", "env_var"):
                if key not in entry:
                    raise ConfigurationError(
                        f"SECRET_MAPPINGS entry {idx} is missing required key '{key}'"
                    )
            secrets.append(
                SecretMapping(item=entry["item"], field=entry["field"], env_var=entry["env_var"])
            )

        return cls(onepassword=op_config, ecs=ecs_config, secrets=secrets)
