from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IJobQueue(Protocol):
    async def enqueue_prediction(self, *, job_id: UUID) -> None: ...
