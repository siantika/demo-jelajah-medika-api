from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis

from apps.api_service.src.application.ports.job_queue import IJobQueue


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

        self._queue_key = queue_key

    async def enqueue_prediction(
       self,
       *,
       job_id: UUID,
    ) -> None:

       await self._client.lpush(
        self._queue_key,
        str(job_id),
        )