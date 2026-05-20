from __future__ import annotations

from typing import Callable

from apps.shared.job_management.contracts.prediction_engine import PredictionEngine
from apps.shared.job_management.contracts.repositories.prediction_job_repository import (
    PredictionJobRepository,
)

_repository_factory: Callable[[], PredictionJobRepository] | None = None


def configure_repository_factory(factory: Callable[[], PredictionJobRepository]) -> None:
    global _repository_factory
    _repository_factory = factory


def get_repository() -> PredictionJobRepository:
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
