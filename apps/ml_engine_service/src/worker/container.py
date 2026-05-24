from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.ml_engine_service.src.application.ports.i_job_queue import IJobQueue
from apps.ml_engine_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.ml_engine_service.src.infra.queue.redis_queue_job import RedisJobQueue
from apps.ml_engine_service.src.infra.repositories.sqlalchemy_prediction_job_repository import (
    SQLAlchemyPredictionJobRepository,
)
from apps.shared.contracts.prediction_engine import PredictionEngine

_repository_factory: Callable[[], IPredictionJobRepository] | None = None


@dataclass(frozen=True)
class WorkerSettings:
    database_url: str
    redis_url: str
    queue_key: str
    assets_root: str
    poll_interval: float
    on_error: str
    gnn_features: int
    gnn_depth: int
    mlp_depth: int


@dataclass(frozen=True)
class MLQueue:
    QUEUED: str = "queue:ml:queued"
    PROCESSING: str = "queue:ml:processing"
    RETRY: str = "queue:ml:retry"
    DLQ: str = "queue:ml:dlq"


def _load_env_file() -> dict[str, str]:
    env_file = Path(".env")
    if not env_file.exists():
        return {}

    values: dict[str, str] = {}

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed = value.strip().strip('"').strip("'")
        values[key.strip().upper()] = parsed
    return values


def _read_setting(env_values: dict[str, str], *keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value is not None and value != "":
            return value
    for key in keys:
        value = env_values.get(key.upper())
        if value is not None and value != "":
            return value
    return default


def load_worker_settings() -> WorkerSettings:
    env_values = _load_env_file()

    database_url = _read_setting(env_values, "DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required (env var or .env at project root)")

    on_error = _read_setting(env_values, "ML_WORKER_ON_ERROR", default="requeue")
    assert on_error is not None
    if on_error not in ("requeue", "dlq"):
        raise RuntimeError("ML_WORKER_ON_ERROR must be one of: requeue, dlq")

    poll_interval_raw = _read_setting(
        env_values,
        "ML_WORKER_POLL_INTERVAL",
        default="1",
    )
    assert poll_interval_raw is not None

    return WorkerSettings(
        database_url=database_url,
        redis_url=_read_setting(env_values, "REDIS_URL", default="redis://localhost:6379/0") or "redis://localhost:6379/0",
        queue_key=_read_setting(
            env_values,
            "ML_QUEUE_KEY",
            "REDIS_QUEUE_KEY",
            default=MLQueue.QUEUED,
        )
        or MLQueue.QUEUED,
        assets_root=_read_setting(env_values, "ML_ASSETS_ROOT", default=".") or ".",
        poll_interval=float(poll_interval_raw),
        on_error=on_error,
        gnn_features=int(_read_setting(env_values, "ML_GNN_FEATURES", default="40") or "40"),
        gnn_depth=int(_read_setting(env_values, "ML_GNN_DEPTH", default="3") or "3"),
        mlp_depth=int(_read_setting(env_values, "ML_MLP_DEPTH", default="2") or "2"),
    )


def get_job_queue(settings: WorkerSettings) -> IJobQueue:
    return RedisJobQueue(redis_url=settings.redis_url, queue_key=settings.queue_key)


def create_session_factory(settings: WorkerSettings) -> async_sessionmaker[AsyncSession]:
    engine_db = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(
        bind=engine_db,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def dispose_session_factory(session_factory: async_sessionmaker[AsyncSession]) -> None:
    engine = session_factory.kw.get("bind")
    if engine is None:
        return
    await engine.dispose()


def create_repository_from_session(session: AsyncSession) -> IPredictionJobRepository:
    return SQLAlchemyPredictionJobRepository(db=session)


def configure_repository_factory(factory: Callable[[], IPredictionJobRepository]) -> None:
    global _repository_factory
    _repository_factory = factory


def get_repository() -> IPredictionJobRepository:
    if _repository_factory is None:
        raise RuntimeError(
            "PredictionJobRepository factory is not configured for worker. "
            "Call configure_repository_factory(...) during worker startup."
        )
    return _repository_factory()


def get_prediction_engine() -> PredictionEngine:
    from apps.ml_engine_service.src.infra.integrations.gnn_predictor import (
        GNNPredictionEngine,
    )

    # Assets root is relative to project root by default.
    return GNNPredictionEngine(assets_root=".")


def get_prediction_engine_from_settings(settings: WorkerSettings) -> PredictionEngine:
    from apps.ml_engine_service.src.infra.integrations.gnn_predictor import (
        GNNPredictionEngine,
    )

    return GNNPredictionEngine(
        assets_root=settings.assets_root,
        args={
            "features": settings.gnn_features,
            "GNN_depth": settings.gnn_depth,
            "MLP_depth": settings.mlp_depth,
            "mode": "regression",
        },
    )
