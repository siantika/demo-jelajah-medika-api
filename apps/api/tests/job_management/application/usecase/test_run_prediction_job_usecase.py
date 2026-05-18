from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from apps.shared.job_management.domain.entities.prediction_job import PredictionJob
from apps.shared.job_management.domain.value_objects.dataset import Dataset
from apps.shared.job_management.domain.value_objects.job_status import JobStatusEnum
from apps.shared.job_management.domain.value_objects.model_version import ModelVersion
from apps.shared.job_management.domain.value_objects.options import Options
from apps.shared.job_management.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.job_management.domain.value_objects.smiles import Smiles
from apps.ml_engine_service.src.application.usecase.run_prediction_job_usecase import (
    PredictionJobNotFoundError,
    RunPredictionJobCmd,
    RunPredictionJobUseCase,
)


class FakePredictionJobRepository:
    def __init__(self, jobs: dict[UUID, PredictionJob]):
        self.jobs = jobs
        self.saved_jobs: list[PredictionJob] = []

    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        return self.jobs.get(job_id)

    def save(self, *, job: PredictionJob) -> None:
        self.jobs[job.id] = job
        self.saved_jobs.append(job)


class SuccessfulEngine:
    def predict(
        self,
        *,
        smiles: str,
        dataset_name: str,
        model_version: str,
        top_k: int,
        return_sequences: bool,
    ) -> list[PredictionResultItem]:
        return [PredictionResultItem(affinity=0.91, target_sequence="ACDEFGHIK")]


class FailingEngine:
    def predict(
        self,
        *,
        smiles: str,
        dataset_name: str,
        model_version: str,
        top_k: int,
        return_sequences: bool,
    ) -> list[PredictionResultItem]:
        raise RuntimeError("model inference failed")


def _make_pending_job() -> PredictionJob:
    return PredictionJob(
        id=uuid4(),
        smiles=Smiles("CCO"),
        dataset=Dataset(name="KIBA"),
        options=Options(top_k=10, return_sequence=True),
        model_version=ModelVersion("gnn-1.0.0"),
    )


def test_run_prediction_job_marks_success_and_persists() -> None:
    job = _make_pending_job()
    repository = FakePredictionJobRepository(jobs={job.id: job})
    usecase = RunPredictionJobUseCase(
        repository=repository,
        prediction_engine=SuccessfulEngine(),
    )

    usecase.execute(RunPredictionJobCmd(job_id=job.id))

    updated = repository.jobs[job.id]
    assert updated.status.value == JobStatusEnum.SUCCESS
    assert len(updated.result) == 1
    assert updated.error is None
    assert len(repository.saved_jobs) == 2


def test_run_prediction_job_marks_failed_when_engine_raises() -> None:
    job = _make_pending_job()
    repository = FakePredictionJobRepository(jobs={job.id: job})
    usecase = RunPredictionJobUseCase(
        repository=repository,
        prediction_engine=FailingEngine(),
    )

    with pytest.raises(RuntimeError):
        usecase.execute(RunPredictionJobCmd(job_id=job.id))

    updated = repository.jobs[job.id]
    assert updated.status.value == JobStatusEnum.FAILED
    assert updated.error == "model inference failed"
    assert updated.result == []
    assert len(repository.saved_jobs) == 2


def test_run_prediction_job_raises_not_found() -> None:
    repository = FakePredictionJobRepository(jobs={})
    usecase = RunPredictionJobUseCase(
        repository=repository,
        prediction_engine=SuccessfulEngine(),
    )

    with pytest.raises(PredictionJobNotFoundError):
        usecase.execute(RunPredictionJobCmd(job_id=uuid4()))
