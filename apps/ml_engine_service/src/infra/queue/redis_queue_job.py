from uuid import UUID

from redis.asyncio import Redis


class RedisJobQueue:

    def __init__(
        self,
        *,
        redis_url: str,
        queue_key: str,
    ):
        self._client = Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        self._queued_key = queue_key
        if queue_key.endswith(":queued"):
            key_prefix = queue_key[: -len(":queued")]
            self._processing_key = f"{key_prefix}:processing"
            self._retry_key = f"{key_prefix}:retry"
            self._dlq_key = f"{key_prefix}:dlq"
        else:
            self._processing_key = f"{queue_key}:processing"
            self._retry_key = f"{queue_key}:retry"
            self._dlq_key = f"{queue_key}:dlq"
        self._retry_count_key = f"{self._queued_key}:retry_count"

    async def enqueue(
        self,
        *,
        job_id: UUID,
    ) -> None:
        await self._client.lpush(
            self._queued_key,
            str(job_id),
        )

    async def dequeue(self) -> UUID | None:
        raw_job_id = await self._client.rpoplpush(
            self._queued_key,
            self._processing_key,
        )
        if raw_job_id is None:
            return None
        return UUID(raw_job_id)

    async def ack(
        self,
        *,
        job_id: UUID,
    ) -> None:
        await self._client.lrem(
            self._processing_key,
            1,
            str(job_id),
        )

    async def requeue(
        self,
        *,
        job_id: UUID,
    ) -> None:
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.lrem(self._processing_key, 1, str(job_id))
            pipe.lpush(self._retry_key, str(job_id))
            await pipe.execute()

    async def move_to_dlq(
        self,
        *,
        job_id: UUID,
    ) -> None:
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.lrem(self._processing_key, 1, str(job_id))
            pipe.lpush(self._dlq_key, str(job_id))
            await pipe.execute()

    async def promote_retry(self) -> UUID | None:
        raw_job_id = await self._client.rpoplpush(
            self._retry_key,
            self._queued_key,
        )
        if raw_job_id is None:
            return None
        return UUID(raw_job_id)

    async def increment_retry_count(self, *, job_id: UUID) -> int:
        return int(await self._client.hincrby(self._retry_count_key, str(job_id), 1))

    async def clear_retry_count(self, *, job_id: UUID) -> None:
        await self._client.hdel(self._retry_count_key, str(job_id))
