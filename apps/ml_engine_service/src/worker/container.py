from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.ml_engine_service.src.infra.integrations.gnn_predictor import (
    GNNPredictionEngine,
)
from apps.ml_engine_service.src.infra.queue.redis_queue_job import RedisJobQueue
from apps.ml_engine_service.src.worker.config import WorkerSettings
from apps.shared.src.contracts.i_job_queue import (
    IPredictionJobQueueConsumer as IJobQueue,
)
from apps.shared.src.contracts.prediction_engine import PredictionEngine
from apps.shared.src.contracts.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.shared.src.infra.db.session import (
    close_db_engine,
    get_session_factory,
)
from apps.shared.src.infra.repositories.sqlalchemy_prediction_job_repository import (
    SQLAlchemyPredictionJobRepository,
)


def get_job_queue(settings: WorkerSettings) -> IJobQueue:
    return RedisJobQueue(redis_url=settings.redis_url, queue_key=settings.queue_key)


def create_session_factory(settings: WorkerSettings) -> async_sessionmaker[AsyncSession]:
    return get_session_factory(settings.database_url)


async def dispose_session_factory(session_factory: async_sessionmaker[AsyncSession]) -> None:
    engine = session_factory.kw.get("bind")
    await close_db_engine(str(engine.url) if engine is not None else None)


def create_repository_from_session(session: AsyncSession) -> IPredictionJobRepository:
    return SQLAlchemyPredictionJobRepository(db=session)


def get_prediction_engine_from_settings(settings: WorkerSettings) -> PredictionEngine:

    return GNNPredictionEngine(
        assets_root=settings.assets_root,
        args={
            "features": settings.gnn_features,
            "GNN_depth": settings.gnn_depth,
            "MLP_depth": settings.mlp_depth,
            "mode": "regression",
        },
    )
