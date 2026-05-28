"""
    Dependency providers for the application.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api_service.src.application.ports.smiles_validator import ISmilesValidator
from apps.api_service.src.application.usecase.create_prediction_usecase import (
    CreatePredictionJobUseCase,
)
from apps.api_service.src.application.usecase.get_prediction_job_usecase import (
    GetPredictionJobUseCase,
)
from apps.api_service.src.application.usecase.get_queue_metrics_usecase import (
    GetQueueMetricsUseCase,
)
from apps.api_service.src.infra.queue.redis_job_queue import RedisJobQueue
from apps.api_service.src.infra.repositories.redis_queue_repository import (
    RedisQueueRepository,
)
from apps.api_service.src.infra.smiles_validator_default import DomainSmilesValidator
from apps.api_service.src.shared.settings.config import settings
from apps.shared.src.contracts.i_job_queue import (
    IPredictionJobQueueProducer as IJobQueue,
)
from apps.shared.src.contracts.i_prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.shared.src.contracts.i_repo_queue import IRepoQueue
from apps.shared.src.infra.db.session import db_session_dependency
from apps.shared.src.infra.repositories.sqlalchemy_prediction_job_repository import (
    SQLAlchemyPredictionJobRepository,
)
from apps.shared.src.queues import MLQueue


def get_repository(
    db: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> IPredictionJobRepository:
    return SQLAlchemyPredictionJobRepository(db=db)

def get_job_queue() -> IJobQueue:
    return RedisJobQueue(
        redis_url=settings.redis_url,
        queue_key=MLQueue.QUEUED,
    )

def get_smiles_validator() -> ISmilesValidator:
    return DomainSmilesValidator()


def get_redis_client() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


def get_queue_repository(
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> IRepoQueue:
    return RedisQueueRepository(redis=redis)

def get_create_prediction_usecase(
    repository: Annotated[IPredictionJobRepository, Depends(get_repository)],
    job_queue: Annotated[IJobQueue, Depends(get_job_queue)],
    smiles_validator: Annotated[ISmilesValidator, Depends(get_smiles_validator)],
) -> CreatePredictionJobUseCase:
    return CreatePredictionJobUseCase(
        repository=repository,
        job_queue=job_queue,
        smiles_validator=smiles_validator,
    )

def get_prediction_job_usecase(
    repository: Annotated[IPredictionJobRepository, Depends(get_repository)],
) -> GetPredictionJobUseCase:
    return GetPredictionJobUseCase(repository=repository)


def get_queue_metrics_usecase(
    queue_repository: Annotated[IRepoQueue, Depends(get_queue_repository)],
) -> GetQueueMetricsUseCase:
    return GetQueueMetricsUseCase(queue_repository=queue_repository)


CreatePredictionUseCaseDep = Annotated[CreatePredictionJobUseCase, Depends(get_create_prediction_usecase)]
GetPredictionJobUseCaseDep = Annotated[GetPredictionJobUseCase, Depends(get_prediction_job_usecase)]
GetQueueMetricsUseCaseDep = Annotated[GetQueueMetricsUseCase, Depends(get_queue_metrics_usecase)]
RepositoryDep = Annotated[IPredictionJobRepository, Depends(get_repository)]
