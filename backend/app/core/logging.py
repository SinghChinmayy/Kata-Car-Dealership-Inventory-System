import json
import logging
from datetime import datetime, timezone
from typing import Any

SENSITIVE_FIELD_NAMES = frozenset({"authorization", "password", "token", "jwt", "secret"})


def redact(value: Any, field_name: str = "") -> Any:
    """Return a recursively safe representation suitable for application logs."""
    if field_name.lower() in SENSITIVE_FIELD_NAMES:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {key: redact(item, key) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Render only explicitly supplied structured fields as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        extra = getattr(record, "structured", {})
        payload.update(redact(extra))
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("app")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # Propagation lets test/host collectors receive the same structured record.
    logger.propagate = True


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    logger.info(message, extra={"structured": redact(fields)})
