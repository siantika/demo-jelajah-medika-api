from __future__ import annotations

import os

from celery import Celery

from apps.ml_engine_service.src.infra.repositories.in_memory_prediction_job_repository import (
    InMemoryPredictionJobRepository,
)
from apps.ml_engine_service.src.infra.repositories.sqlalchemy_prediction_job_repository import (
    SQLAlchemyPredictionJobRepository,
)
from apps.ml_engine_service.src.worker.container import configure_repository_factory

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "ml_engine_worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

repository_backend = os.getenv("PREDICTION_REPOSITORY_BACKEND", "postgres").lower()
if repository_backend == "inmemory":
    _default_repository = InMemoryPredictionJobRepository()
else:
    _default_repository = SQLAlchemyPredictionJobRepository(
        database_url=os.getenv("DATABASE_URL"),
    )

configure_repository_factory(lambda: _default_repository)

# Ensure task module is loaded.
celery_app.autodiscover_tasks(
    packages=["apps.ml_engine_service.src.worker"],
    force=True,
)
