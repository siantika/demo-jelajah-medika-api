from __future__ import annotations

from apps.api_service.src.application.dto import QueueMetricsResult
from apps.shared.src.contracts.i_repo_queue import IRepoQueue


class GetQueueMetricsUseCase:
    def __init__(self, queue_repository: IRepoQueue):
        self._queue_repository = queue_repository

    async def execute(self) -> QueueMetricsResult:
        queued, processing, retry, dlq = await self._queue_repository.get_metrics()

        return QueueMetricsResult(
            queued=queued,
            processing=processing,
            retry=retry,
            dlq=dlq,
        )
