from __future__ import annotations

import asyncio
import signal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.ml_engine_service.src.application.usecase.dto import RunPredictionJobCmd
from apps.ml_engine_service.src.application.usecase.run_prediction_job_usecase import (
    RunPredictionJobUseCase,
)
from apps.ml_engine_service.src.worker.container import (
    create_repository_from_session,
    create_session_factory,
    dispose_session_factory,
    get_job_queue,
    get_prediction_engine_from_settings,
    load_worker_settings,
)


async def _handle_one_job(
    *,
    queue,
    session_factory: async_sessionmaker[AsyncSession],
    prediction_engine,
    on_error: str,
) -> None:
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
        await queue.ack(job_id=job_id)
        print(f"[worker] success job_id={job_id}")
    except Exception as err:
        if on_error == "dlq":
            await queue.move_to_dlq(job_id=job_id)
            print(f"[worker] failed->dlq job_id={job_id} error={err}")
        else:
            await queue.requeue(job_id=job_id)
            print(f"[worker] failed->requeue job_id={job_id} error={err}")


async def _main() -> None:
    """
        setup worker till running it in a loop
    
    """
    
    settings = load_worker_settings()
    queue = get_job_queue(settings)
    prediction_engine = get_prediction_engine_from_settings(settings)
    session_factory = create_session_factory(settings)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    
    # Gracefully shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    print(
        "[worker] started "
        f"queue_key={settings.queue_key} on_error={settings.on_error} "
        f"poll_interval={settings.poll_interval}s"
    )
    try:
        while not stop_event.is_set():
            await _handle_one_job(
                queue=queue,
                session_factory=session_factory,
                prediction_engine=prediction_engine,
                on_error=settings.on_error,
            )
            await asyncio.sleep(settings.poll_interval)
    finally:
        await dispose_session_factory(session_factory)
        print("[worker] stopped")


if __name__ == "__main__":
    asyncio.run(_main())
