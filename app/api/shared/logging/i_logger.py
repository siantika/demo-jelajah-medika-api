from abc import ABC, abstractmethod
from typing import Any


class ILogger(ABC):
    @abstractmethod
    def info(self, event: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def error(self, event: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def warning(self, event: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def debug(self, event: str, **kwargs: Any) -> None:
        pass
