from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from apps.api.src.job_management_api.application.dto import GetPredictionJobQuery
from apps.api.src.job_management_api.application.usecase.get_prediction_job_usecase import (
    GetPredictionJobUseCase,
    PredictionJobNotFoundError,
)

from apps.shared.job_management_domain.domain.entities.prediction_job import (
    PredictionJob,
)
from apps.shared.job_management_domain.domain.value_objects.dataset import Dataset
from apps.shared.job_management_domain.domain.value_objects.model_version import (
    ModelVersion,
)
from apps.shared.job_management_domain.domain.value_objects.options import Options
from apps.shared.job_management_domain.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.job_management_domain.domain.value_objects.smiles import Smiles


class FakePredictionJobRepository:
    def __init__(self, jobs: dict[UUID, PredictionJob]):
        self.jobs = jobs

    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        return self.jobs.get(job_id)


def _make_success_job() -> PredictionJob:
    job = PredictionJob(
        id=uuid4(),
        smiles=Smiles("CCO"),
        dataset=Dataset(name="KIBA"),
        options=Options(top_k=5, return_sequence=True),
        model_version=ModelVersion("gnn-1.0.0"),
        created_at=datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc),
    )
    job.mark_running(now=datetime(2026, 5, 18, 8, 1, tzinfo=timezone.utc))
    job.mark_success(
        [PredictionResultItem(affinity=0.91, target_sequence="ACDEFGHIK")],
        now=datetime(2026, 5, 18, 8, 2, tzinfo=timezone.utc),
    )
    return job


def test_get_prediction_job_returns_mapped_result() -> None:
    job = _make_success_job()
    repo = FakePredictionJobRepository(jobs={job.id: job})
    usecase = GetPredictionJobUseCase(repository=repo)

    result = usecase.execute(GetPredictionJobQuery(job_id=job.id))

    assert result.job_id == job.id
    assert result.status == "SUCCESS"
    assert result.created_at == job.created_at
    assert result.updated_at == job.updated_at
    assert result.result == [{"affinity": 0.91, "target_sequence": "ACDEFGHIK"}]
    assert result.metrics is None
    assert result.error_code is None
    assert result.error_message is None


def test_get_prediction_job_raises_when_not_found() -> None:
    repo = FakePredictionJobRepository(jobs={})
    usecase = GetPredictionJobUseCase(repository=repo)

    with pytest.raises(PredictionJobNotFoundError):
        usecase.execute(GetPredictionJobQuery(job_id=uuid4()))
