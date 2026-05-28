from __future__ import annotations

import asyncio
import signal

from apps.ml_engine_service.src.worker.config import load_worker_settings
from apps.ml_engine_service.src.worker.container import (
    create_session_factory,
    dispose_session_factory,
    get_job_queue,
    get_prediction_engine_from_settings,
)
from apps.ml_engine_service.src.worker.job_handler import JobHandlerDeps, handle_one_job
from apps.shared.src.infra.logging import StructlogLogger, setup_logger

logger = StructlogLogger("ml_worker")


async def _main() -> None:
    settings = load_worker_settings()
    setup_logger(json_format=True, log_level="INFO")
    queue = get_job_queue(settings)
    prediction_engine = get_prediction_engine_from_settings(settings)
    session_factory = create_session_factory(settings)
    handler_deps = JobHandlerDeps(
        queue=queue,
        session_factory=session_factory,
        prediction_engine=prediction_engine,
        max_retries=settings.max_retries,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    
    # Gracefully shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info(
        "worker_started",
        queue_key=settings.queue_key,
        poll_interval=settings.poll_interval,
        max_retries=settings.max_retries,
    )
    try:
        while not stop_event.is_set():
            await handle_one_job(handler_deps)
            await asyncio.sleep(settings.poll_interval)
    finally:
        await dispose_session_factory(session_factory)
        logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(_main())
