from typing import Any

import structlog

from apps.api_service.src.shared.logging.i_logger import ILogger


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
