"""Orchestration: fetch secrets from 1Password and inject into an ECS task definition."""

from __future__ import annotations

from .config import InjectorConfig
from .ecs import ECSClient
from .onepassword import OnePasswordClient


class SecretInjector:
    """Fetches secrets from 1Password Connect and injects them into an ECS task definition."""

    def __init__(self, config: InjectorConfig) -> None:
        self._config = config
        self._op = OnePasswordClient(config.onepassword)
        self._ecs = ECSClient(config.ecs)

    def inject(self) -> str:
        """Fetch all configured secrets and register a new ECS task definition revision.

        Returns
        -------
        str
            The ARN of the newly registered task definition revision.
        """
        secrets = self._op.get_secrets(self._config.secrets)
        return self._ecs.register_task_definition_with_env(secrets)
