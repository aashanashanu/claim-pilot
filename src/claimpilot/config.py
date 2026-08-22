from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    env: str = "development"
    aws_region: str | None = None
    aws_default_region: str | None = None
    claimpilot_model_id: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            env=os.getenv("CLAIMPILOT_ENV", "development"),
            aws_region=os.getenv("AWS_REGION"),
            aws_default_region=os.getenv("AWS_DEFAULT_REGION"),
            claimpilot_model_id=os.getenv("CLAIMPILOT_MODEL_ID"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        )


DEFAULT_CONFIG = AppConfig.from_env()
