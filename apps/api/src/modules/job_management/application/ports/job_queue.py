from __future__ import annotations

from typing import Protocol
from uuid import UUID


class JobQueue(Protocol):
    def enqueue_prediction(self, *, prediction_id: UUID) -> str: ...
