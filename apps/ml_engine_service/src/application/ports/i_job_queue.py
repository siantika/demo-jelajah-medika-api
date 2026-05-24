from typing import Protocol
from uuid import UUID


class IJobQueue(Protocol):

    async def enqueue(
        self,
        *,
        job_id: UUID,
    ) -> None:
        ...

    async def dequeue(self) -> UUID | None:
        ...

    async def ack(
        self,
        *,
        job_id: UUID,
    ) -> None:
        ...

    async def requeue(
        self,
        *,
        job_id: UUID,
    ) -> None:
        ...

    async def move_to_dlq(
        self,
        *,
        job_id: UUID,
    ) -> None:
        ...

    async def promote_retry(self) -> UUID | None:
        ...

    async def increment_retry_count(self, *, job_id: UUID) -> int:
        ...

    async def clear_retry_count(self, *, job_id: UUID) -> None:
        ...
