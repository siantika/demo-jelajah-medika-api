from datetime import datetime, timezone
from uuid import uuid4

import pytest

from apps.shared.job_management_domain.domain.entities.prediction_job import PredictionJob
from apps.shared.job_management_domain.domain.exceptions import InvalidValueObject
from apps.shared.job_management_domain.domain.value_objects.dataset import Dataset
from apps.shared.job_management_domain.domain.value_objects.job_status import JobStatusEnum
from apps.shared.job_management_domain.domain.value_objects.model_version import ModelVersion
from apps.shared.job_management_domain.domain.value_objects.options import Options
from apps.shared.job_management_domain.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.job_management_domain.domain.value_objects.smiles import Smiles


def make_job() -> PredictionJob:
    return PredictionJob(
        id=uuid4(),
        smiles=Smiles("CCO"),
        dataset=Dataset(name="KIBA"),
        options=Options(top_k=5, return_sequence=True),
        model_version=ModelVersion("gnn-1.0.0"),
    )


def test_default_status_is_pending() -> None:
    job = make_job()

    assert job.status.value == JobStatusEnum.PENDING
    assert job.status.value.value == "PENDING"
    assert job.result == []
    assert job.error is None


def test_mark_running_from_pending() -> None:
    job = make_job()
    now = datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc)

    job.mark_running(now=now)

    assert job.status.value == JobStatusEnum.RUNNING
    assert job.updated_at == now


def test_mark_success_from_running() -> None:
    job = make_job()
    job.mark_running()

    result = [PredictionResultItem(affinity=0.91, target_sequence="ACDEFGHIK")]
    now = datetime(2026, 5, 18, 8, 5, tzinfo=timezone.utc)
    job.mark_success(result, now=now)

    assert job.status.value == JobStatusEnum.SUCCESS
    assert job.result == result
    assert job.error is None
    assert job.updated_at == now


def test_mark_failed_from_running() -> None:
    job = make_job()
    job.mark_running()

    job.mark_failed("inference timeout")

    assert job.status.value == JobStatusEnum.FAILED
    assert job.error == "inference timeout"
    assert job.result == []


def test_mark_running_rejects_non_pending() -> None:
    job = make_job()
    job.mark_running()

    with pytest.raises(InvalidValueObject):
        job.mark_running()


def test_mark_success_rejects_non_running() -> None:
    job = make_job()

    with pytest.raises(InvalidValueObject):
        job.mark_success([PredictionResultItem(affinity=0.5, target_sequence="ACDEFG")])


def test_mark_failed_rejects_empty_message() -> None:
    job = make_job()
    job.mark_running()

    with pytest.raises(InvalidValueObject):
        job.mark_failed("   ")
