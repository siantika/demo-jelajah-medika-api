import logging
import sys

import structlog


def _mask_sensitive_fields(_, __, event_dict):
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
    if structlog.is_configured():
        return

    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level.upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {log_level}. Use one of {valid_levels}")

    level = getattr(logging, log_level.upper())

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

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
        _mask_sensitive_fields,
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
