from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class MLQueue:
    QUEUED:Final[str] = "queue:ml:queued"
    PROCESSING: Final[str] = "queue:ml:processing"
    RETRY: Final[str] = "queue:ml:retry"
    DLQ: Final[str] = "queue:ml:dlq"
