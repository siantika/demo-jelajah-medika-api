from __future__ import annotations

import asyncio
import signal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.ml_engine_service.src.application.usecase.dto import RunPredictionJobCmd
from apps.ml_engine_service.src.application.usecase.run_prediction_job_usecase import (
    RunPredictionJobUseCase,
)
from apps.shared.src.domain.errors import MLInferenceError, PredictionJobNotFoundError
from apps.shared.src.domain.exceptions import InvalidValueObject
from apps.shared.src.infra.logging import StructlogLogger, setup_logger
from apps.ml_engine_service.src.worker.container import (
    create_repository_from_session,
    create_session_factory,
    dispose_session_factory,
    get_job_queue,
    get_prediction_engine_from_settings,
    load_worker_settings,
)

logger = StructlogLogger("ml_worker")


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


async def _handle_one_job(
    *,
    queue,
    session_factory: async_sessionmaker[AsyncSession],
    prediction_engine,
    on_error: str,
    max_retries: int,
) -> None:
    await queue.promote_retry()
    job_id = await queue.dequeue()
    if job_id is None:
        return

    try:
        async with session_factory() as session:
            repository = create_repository_from_session(session)
            usecase = RunPredictionJobUseCase(
                repository=repository,
                prediction_engine=prediction_engine,
            )
            await usecase.execute(RunPredictionJobCmd(job_id=job_id))
        await queue.clear_retry_count(job_id=job_id)
        await queue.ack(job_id=job_id)
        logger.info("worker_job_success", job_id=str(job_id))
    except Exception as err:
        if _is_non_retryable_error(err):
            await queue.move_to_dlq(job_id=job_id)
            await queue.clear_retry_count(job_id=job_id)
            logger.error(
                "worker_job_failed_non_retryable_to_dlq",
                job_id=str(job_id),
                error=str(err),
            )
            return

        if on_error == "dlq":
            await queue.move_to_dlq(job_id=job_id)
            await queue.clear_retry_count(job_id=job_id)
            logger.error("worker_job_failed_to_dlq", job_id=str(job_id), error=str(err))
        else:
            retry_count = await queue.increment_retry_count(job_id=job_id)
            if retry_count > max_retries:
                await queue.move_to_dlq(job_id=job_id)
                await queue.clear_retry_count(job_id=job_id)
                logger.error(
                    "worker_job_failed_to_dlq_max_retries",
                    job_id=str(job_id),
                    retries=retry_count,
                    max_retries=max_retries,
                    error=str(err),
                )
            else:
                await queue.requeue(job_id=job_id)
                logger.warning(
                    "worker_job_failed_to_retry",
                    job_id=str(job_id),
                    retries=retry_count,
                    max_retries=max_retries,
                    error=str(err),
                )


async def _main() -> None:
    """
        setup worker till running it in a loop
    
    """
    
    settings = load_worker_settings()
    setup_logger(json_format=True, log_level="INFO")
    queue = get_job_queue(settings)
    prediction_engine = get_prediction_engine_from_settings(settings)
    session_factory = create_session_factory(settings)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    
    # Gracefully shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info(
        "worker_started",
        queue_key=settings.queue_key,
        on_error=settings.on_error,
        poll_interval=settings.poll_interval,
        max_retries=settings.max_retries,
    )
    try:
        while not stop_event.is_set():
            await _handle_one_job(
                queue=queue,
                session_factory=session_factory,
                prediction_engine=prediction_engine,
                on_error=settings.on_error,
                max_retries=settings.max_retries,
            )
            await asyncio.sleep(settings.poll_interval)
    finally:
        await dispose_session_factory(session_factory)
        logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(_main())
