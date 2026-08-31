from __future__ import annotations

import json
import os
from dataclasses import dataclass


RUNTIME_SECRETS_ENV = "CLAIMPILOT_RUNTIME_SECRETS_JSON"


def load_runtime_secrets() -> dict[str, str]:
    raw = os.getenv(RUNTIME_SECRETS_ENV, "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{RUNTIME_SECRETS_ENV} must contain valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"{RUNTIME_SECRETS_ENV} must contain a JSON object.")

    return {str(key): "" if value is None else str(value) for key, value in parsed.items()}


def runtime_secret_value(key: str, default: str | None = None) -> str | None:
    secrets = load_runtime_secrets()
    if key in secrets:
        return secrets[key]
    return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class AppConfig:
    env: str = "development"
    aws_region: str | None = None
    aws_default_region: str | None = None
    claimpilot_model_id: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    gmail_credentials_json: str | None = None
    gmail_token_json: str | None = None
    gmail_target_email: str | None = None
    gmail_query: str | None = None
    gmail_polling_enabled: bool = True
    gmail_poll_interval_seconds: int = 60
    gmail_poll_max_results: int = 10

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            env=os.getenv("CLAIMPILOT_ENV", "development"),
            aws_region=os.getenv("AWS_REGION") or runtime_secret_value("aws_region"),
            aws_default_region=os.getenv("AWS_DEFAULT_REGION") or runtime_secret_value("aws_default_region"),
            claimpilot_model_id=os.getenv("CLAIMPILOT_MODEL_ID") or runtime_secret_value("claimpilot_model_id"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or runtime_secret_value("aws_access_key_id"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") or runtime_secret_value("aws_secret_access_key"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN") or runtime_secret_value("aws_session_token"),
            gmail_credentials_json=os.getenv("GMAIL_CREDENTIALS_JSON") or runtime_secret_value("gmail_credentials_json"),
            gmail_token_json=os.getenv("GMAIL_TOKEN_JSON") or runtime_secret_value("gmail_token_json"),
            gmail_target_email=os.getenv("CLAIMPILOT_GMAIL_TARGET_ADDRESS") or runtime_secret_value("gmail_target_address"),
            gmail_query=os.getenv("CLAIMPILOT_GMAIL_QUERY") or runtime_secret_value("gmail_query"),
            gmail_polling_enabled=_env_bool("CLAIMPILOT_GMAIL_POLLING_ENABLED", default=True),
            gmail_poll_interval_seconds=_env_int("CLAIMPILOT_GMAIL_POLL_INTERVAL_SECONDS", default=60),
            gmail_poll_max_results=_env_int("CLAIMPILOT_GMAIL_POLL_MAX_RESULTS", default=10),
        )


DEFAULT_CONFIG = AppConfig.from_env()
