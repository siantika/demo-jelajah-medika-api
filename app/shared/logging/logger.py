import logging
import sys
from typing import Any

import structlog

from app.shared.logging.i_logger import ILogger


def _mask_sensitive_fields(_, __, event_dict):
    """
    Mask field sensitif secara otomatis.
    Tambahkan key lain sesuai kebutuhan bisnismu.
    """
    sensitive_keys = {
        "password",
        "password_hash",
        "token",
        "secret",
        "api_key",
        "email",
        "phone",
        "card_number",
        "cvv",
        "pin",
    }
    for key in sensitive_keys:
        if key in event_dict:
            event_dict[key] = "[REDACTED]"
    return event_dict


def setup_logger(json_format: bool = True, log_level: str = "INFO") -> None:
    """
    Configure structlog once at startup.
    Safe for uvicorn --reload.
    """
    # Avoid re-configuring on hot reload.
    if structlog.is_configured():
        return

    # Validate log level.
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level.upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {log_level}. Use one of {valid_levels}")

    level = getattr(logging, log_level.upper())

    # Configure root logger.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Build processors.
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _mask_sensitive_fields,  # Automatic sensitive-field masking.
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class StructlogLogger(ILogger):
    def __init__(self, name: str = "app"):
        self._logger = structlog.get_logger(name)

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(event, **kwargs)
