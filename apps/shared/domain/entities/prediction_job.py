from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from apps.shared.domain.exceptions import InvalidValueObject
from apps.shared.domain.value_objects.dataset import Dataset
from apps.shared.domain.value_objects.job_status import JobStatus, JobStatusEnum
from apps.shared.domain.value_objects.model_version import ModelVersion
from apps.shared.domain.value_objects.options import Options
from apps.shared.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.domain.value_objects.smiles import Smiles


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass
class PredictionJob:
    id: UUID
    smiles: Smiles
    dataset: Dataset
    options: Options
    model_version: ModelVersion
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    status: JobStatus = field(default_factory=lambda: JobStatus(JobStatusEnum.PENDING))
    result: List[PredictionResultItem] = field(default_factory=list)
    error: Optional[str] = None

    def __post_init__(self) -> None:
        self.created_at = _to_utc(self.created_at)
        self.updated_at = _to_utc(self.updated_at)
        self._validate_invariants()

    def _resolve_now(self, now: Optional[datetime]) -> datetime:
        if now is None:
            return _utc_now()
        return _to_utc(now)

    def mark_running(self, *, now: Optional[datetime] = None) -> None:
        if self.status.value != JobStatusEnum.PENDING:
            raise InvalidValueObject(
                name="PredictionJob.status",
                reason="Only PENDING job can be marked RUNNING",
                value=self.status.value,
            )
        self.status = JobStatus(JobStatusEnum.RUNNING)
        self.updated_at = self._resolve_now(now)
        self._validate_invariants()

    def mark_success(
        self,
        result: List[PredictionResultItem],
        *,
        now: Optional[datetime] = None,
    ) -> None:
        if self.status.value != JobStatusEnum.RUNNING:
            raise InvalidValueObject(
                name="PredictionJob.status",
                reason="Job must be RUNNING to mark SUCCESS",
                value=self.status.value,
            )
        self.status = JobStatus(JobStatusEnum.SUCCESS)
        self.result = result
        self.error = None
        self.updated_at = self._resolve_now(now)
        self._validate_invariants()

    def mark_failed(self, error: str, *, now: Optional[datetime] = None) -> None:
        if self.status.value != JobStatusEnum.RUNNING:
            raise InvalidValueObject(
                name="PredictionJob.status",
                reason="Job must be RUNNING to mark FAILED",
                value=self.status.value,
            )
        if not error or not error.strip():
            raise InvalidValueObject(
                name="PredictionJob.error",
                reason="Error message cannot be empty",
                value=error,
            )
        self.status = JobStatus(JobStatusEnum.FAILED)
        self.error = error.strip()
        self.result = []
        self.updated_at = self._resolve_now(now)
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if self.status.value in (JobStatusEnum.PENDING, JobStatusEnum.RUNNING):
            if self.error is not None:
                raise InvalidValueObject(
                    name="PredictionJob.error",
                    reason="PENDING/RUNNING job cannot have error",
                    value=self.error,
                )
            if self.result:
                raise InvalidValueObject(
                    name="PredictionJob.result",
                    reason="PENDING/RUNNING job cannot have result",
                    value=self.result,
                )
        if self.status.value == JobStatusEnum.SUCCESS:
            if self.error is not None:
                raise InvalidValueObject(
                    name="PredictionJob.error",
                    reason="SUCCESS job cannot have error",
                    value=self.error,
                )
        if self.status.value == JobStatusEnum.FAILED:
            if self.error is None:
                raise InvalidValueObject(
                    name="PredictionJob.error",
                    reason="FAILED job must have error",
                    value=self.error,
                )
            if self.result:
                raise InvalidValueObject(
                    name="PredictionJob.result",
                    reason="FAILED job cannot have result",
                    value=self.result,
                )
