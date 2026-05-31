# ecs-1password-secret-injector

[![Test](https://github.com/aarongrisez/ecs-1password-secret-injector/actions/workflows/test.yml/badge.svg)](https://github.com/aarongrisez/ecs-1password-secret-injector/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Python library that fetches secrets from [1Password Connect](https://developer.1password.com/docs/connect/) and injects them as environment variables into an AWS ECS task definition.

> **Status:** Early development — the public API may change before `1.0.0`.

## Overview

`ecs-1password-secret-injector` retrieves credentials stored in a 1Password vault and registers a new revision of an ECS task definition with those credentials embedded as container environment variables.

**Typical use case:** run this tool in a CI/CD pipeline before deploying a service to ECS, so that up-to-date secrets from 1Password are always reflected in the running containers—without ever storing secrets in your repository, CI system, or AWS Parameter Store.

## Architecture

```
1Password Connect → OnePasswordClient  ─┐
                                         ├─ SecretInjector ──→ ECS task definition (new revision)
AWS ECS          → ECSClient           ─┘
```

Configuration is loaded entirely from environment variables; see [Configuration](#configuration).

## Requirements

- Python 3.9+
- A running [1Password Connect server](https://developer.1password.com/docs/connect/get-started/)
- AWS credentials with `ecs:DescribeTaskDefinition` and `ecs:RegisterTaskDefinition` permissions

## Installation

```bash
pip install ecs-1password-secret-injector
```

## Configuration

All configuration is supplied through environment variables:

| Variable | Description |
|---|---|
| `OP_CONNECT_URL` | URL of the 1Password Connect server |
| `OP_CONNECT_TOKEN` | API token for the Connect server |
| `OP_VAULT_NAME` | Name of the 1Password vault to read from |
| `AWS_REGION` | AWS region where the ECS cluster is hosted |
| `ECS_CLUSTER` | Name of the ECS cluster |
| `ECS_SERVICE` | Name of the ECS service |
| `ECS_TASK_DEFINITION` | Family name of the ECS task definition to update |
| `SECRET_MAPPINGS` | JSON array of secret mappings; see below |

### `SECRET_MAPPINGS` format

```json
[
  {
    "item": "my-api-key",
    "field": "credential",
    "env_var": "API_KEY"
  },
  {
    "item": "database",
    "field": "password",
    "env_var": "DB_PASSWORD"
  }
]
```

Each entry maps one 1Password item field to one container environment variable name. The secrets are injected into **every** container in the task definition.

## Usage

```python
from ecs_1password_secret_injector import InjectorConfig, SecretInjector

config = InjectorConfig.from_env()
injector = SecretInjector(config)
new_task_def_arn = injector.inject()
print(f"Registered new task definition: {new_task_def_arn}")
```

## Development

### Prerequisites

- Python 3.9+
- [Poetry](https://python-poetry.org/docs/#installation)

### Setup

```bash
git clone https://github.com/aarongrisez/ecs-1password-secret-injector.git
cd ecs-1password-secret-injector
poetry install
```

### Running tests

```bash
poetry run pytest tests
```

To run tests against multiple Python versions locally (requires tox and each Python version installed):

```bash
tox
```

### Linting

```bash
poetry run ruff check src tests
```

## Error handling

All exceptions raised by this library inherit from `InjectorError`. The hierarchy is:

```
InjectorError
├── ConfigurationError   – missing or malformed configuration
├── OnePasswordError     – failure communicating with 1Password Connect
│   └── SecretNotFoundError – a requested item or field does not exist
└── ECSError             – failure communicating with AWS ECS
```

## License

MIT — see [LICENSE](LICENSE).
