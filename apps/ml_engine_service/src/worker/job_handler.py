from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.ml_engine_service.src.application.usecase.dto import RunPredictionJobCmd
from apps.ml_engine_service.src.application.usecase.run_prediction_job_usecase import (
    RunPredictionJobUseCase,
)
from apps.shared.src.domain.errors import MLInferenceError, PredictionJobNotFoundError
from apps.shared.src.domain.exceptions import InvalidValueObject
from apps.shared.src.infra.logging import StructlogLogger

logger = StructlogLogger("ml_worker")


@dataclass(frozen=True)
class JobHandlerDeps:
    queue: object
    session_factory: async_sessionmaker[AsyncSession]
    prediction_engine: object
    max_retries: int


def _is_non_retryable_error(err: Exception) -> bool:
    if isinstance(err, (PredictionJobNotFoundError, InvalidValueObject, FileNotFoundError)):
        return True

    # Inference errors wrap root cause from use case (`raise ... from err`).
    if isinstance(err, MLInferenceError):
        cause = err.__cause__
        if isinstance(cause, (InvalidValueObject, ValueError, TypeError, FileNotFoundError)):
            return True

    message = str(err).lower()
    non_retryable_markers = (
        "unsupported model_version",
        "size mismatch",
        "unexpected key(s) in state_dict",
        "no such file or directory",
    )
    return any(marker in message for marker in non_retryable_markers)


async def _execute_job(
    *,
    job_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
    prediction_engine: object,
) -> None:
    from apps.ml_engine_service.src.worker.container import create_repository_from_session

    async with session_factory() as session:
        repository = create_repository_from_session(session)
        usecase = RunPredictionJobUseCase(
            repository=repository,
            prediction_engine=prediction_engine,
        )
        await usecase.execute(RunPredictionJobCmd(job_id=job_id))


async def _handle_success(*, queue: object, job_id: UUID) -> None:
    await queue.clear_retry_count(job_id=job_id)
    await queue.ack(job_id=job_id)
    logger.info("worker_job_success", job_id=str(job_id))


async def _send_to_dlq(*, queue: object, job_id: UUID, event: str, err: Exception, **extra) -> None:
    await queue.move_to_dlq(job_id=job_id)
    await queue.clear_retry_count(job_id=job_id)
    logger.error(event, job_id=str(job_id), error=str(err), **extra)


async def _handle_failure(
    *,
    queue: object,
    job_id: UUID,
    err: Exception,
    max_retries: int,
) -> None:
    if _is_non_retryable_error(err):
        await _send_to_dlq(
            queue=queue,
            job_id=job_id,
            event="worker_job_failed_non_retryable_to_dlq",
            err=err,
        )
        return

    retry_count = await queue.increment_retry_count(job_id=job_id)
    if retry_count > max_retries:
        await _send_to_dlq(
            queue=queue,
            job_id=job_id,
            event="worker_job_failed_to_dlq_max_retries",
            err=err,
            retries=retry_count,
            max_retries=max_retries,
        )
        return

    await queue.requeue(job_id=job_id)
    logger.warning(
        "worker_job_failed_to_retry",
        job_id=str(job_id),
        retries=retry_count,
        max_retries=max_retries,
        error=str(err),
    )


async def handle_one_job(deps: JobHandlerDeps) -> None:
    await deps.queue.promote_retry()
    job_id = await deps.queue.dequeue()
    if job_id is None:
        return

    try:
        await _execute_job(
            job_id=job_id,
            session_factory=deps.session_factory,
            prediction_engine=deps.prediction_engine,
        )
        await _handle_success(queue=deps.queue, job_id=job_id)
    except Exception as err:
        await _handle_failure(
            queue=deps.queue,
            job_id=job_id,
            err=err,
            max_retries=deps.max_retries,
        )
