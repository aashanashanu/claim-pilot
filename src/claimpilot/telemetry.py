from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


LOGGER = logging.getLogger("claimpilot")

_SENSITIVE_MARKERS = ("token", "secret", "password", "credential", "key")


def _is_sensitive(field_name: str) -> bool:
    lowered = field_name.lower()
    return any(marker in lowered for marker in _SENSITIVE_MARKERS)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): ("***" if _is_sensitive(str(key)) else _sanitize(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize(item) for item in value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def log_event(name: str, **fields: Any) -> None:
    payload = {
        "event": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **_sanitize(fields),
    }
    LOGGER.info(json.dumps(payload, sort_keys=True, default=str))
