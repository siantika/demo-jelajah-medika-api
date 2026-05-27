from __future__ import annotations

from redis.asyncio import Redis

from apps.shared.src.contracts.i_repo_queue import IRepoQueue
from apps.shared.src.queues import MLQueue


class RedisQueueRepository(IRepoQueue):
    def __init__(self, redis: Redis):
        self._redis = redis

    async def get_metrics(self) -> tuple[int, int, int, int]:
        queued_key = MLQueue.QUEUED
        processing_key = MLQueue.PROCESSING
        retry_key = MLQueue.RETRY
        dlq_key = MLQueue.DLQ

        queued, processing, retry, dlq = await self._redis.pipeline(transaction=False).llen(
            queued_key
        ).llen(processing_key).zcard(retry_key).llen(dlq_key).execute()

        return int(queued), int(processing), int(retry), int(dlq)
