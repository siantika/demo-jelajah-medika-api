from __future__ import annotations

from typing import Protocol
from uuid import UUID


class JobQueue(Protocol):
    def enqueue_prediction(self, *, job_id: UUID) -> str: ...
