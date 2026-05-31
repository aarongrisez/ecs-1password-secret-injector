"""ECS client wrapper for updating task definition environment variables."""

from __future__ import annotations

from typing import Any

import boto3
import botocore.exceptions

from .config import ECSConfig
from .exceptions import ECSError

# Read-only fields returned by DescribeTaskDefinition that cannot be
# re-submitted when registering a new revision.
_READONLY_TASK_DEF_KEYS = frozenset(
    {
        "taskDefinitionArn",
        "revision",
        "status",
        "requiresAttributes",
        "compatibilities",
        "registeredAt",
        "registeredBy",
        "deregisteredAt",
    }
)


class ECSClient:
    """Interacts with AWS ECS to register updated task definition revisions."""

    def __init__(self, config: ECSConfig) -> None:
        self._config = config
        self._client = boto3.client("ecs", region_name=config.region)

    def get_current_task_definition(self) -> dict[str, Any]:
        """Return the active task definition for the configured family."""
        try:
            response = self._client.describe_task_definition(
                taskDefinition=self._config.task_definition,
            )
        except botocore.exceptions.ClientError as exc:
            raise ECSError(
                f"Failed to describe task definition '{self._config.task_definition}': {exc}"
            ) from exc
        return response["taskDefinition"]

    def register_task_definition_with_env(
        self, env_vars: dict[str, str]
    ) -> str:
        """Register a new task definition revision with *env_vars* merged into every container.

        Existing environment variables are preserved; values in *env_vars* take precedence
        on key collisions.

        Returns the ARN of the newly registered revision.
        """
        current = self.get_current_task_definition()

        new_def: dict[str, Any] = {
            k: v for k, v in current.items() if k not in _READONLY_TASK_DEF_KEYS
        }

        for container in new_def.get("containerDefinitions", []):
            existing_env = {e["name"]: e["value"] for e in container.get("environment", [])}
            existing_env.update(env_vars)
            container["environment"] = [
                {"name": k, "value": v} for k, v in existing_env.items()
            ]

        try:
            response = self._client.register_task_definition(**new_def)
        except botocore.exceptions.ClientError as exc:
            raise ECSError(
                f"Failed to register new task definition revision: {exc}"
            ) from exc

        return response["taskDefinition"]["taskDefinitionArn"]
