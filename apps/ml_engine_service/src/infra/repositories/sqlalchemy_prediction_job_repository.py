from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.ml_engine_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.shared.domain.entities.prediction_job import PredictionJob
from apps.shared.domain.value_objects.dataset import Dataset
from apps.shared.domain.value_objects.job_status import JobStatus, JobStatusEnum
from apps.shared.domain.value_objects.model_version import ModelVersion
from apps.shared.domain.value_objects.options import Options
from apps.shared.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.domain.value_objects.smiles import Smiles
from apps.shared.infra.db.models.jobs import jobs


class SQLAlchemyPredictionJobRepository(IPredictionJobRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._session = db

    async def save(self, *, job: PredictionJob) -> None:
        stmt = (
            update(jobs)
            .where(jobs.c.id == job.id)
            .values(
                status=self._to_db_status(job.status.value),
                result=[
                    {
                        "affinity": item.affinity,
                        "sequence_target": item.target_sequence,
                        "target_index": None,
                    }
                    for item in job.result
                ],
                error_message=job.error,
                updated_at=job.updated_at,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    @staticmethod
    def _to_db_status(status: JobStatusEnum) -> str:
        status_map = {
            JobStatusEnum.PENDING: "QUEUED",
            JobStatusEnum.RUNNING: "PROCESSING",
            JobStatusEnum.SUCCESS: "COMPLETED",
            JobStatusEnum.FAILED: "FAILED",
        }
        return status_map[status]

    async def find_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        stmt = select(jobs).where(jobs.c.id == job_id)
        row = (await self._session.execute(stmt)).mappings().first()
        if row is None:
            return None
        return self._from_row(dict(row))


    @staticmethod
    def _from_row(row: dict) -> PredictionJob:
        payload = row.get("payload") or {}
        reverse_status_map = {
            "QUEUED": JobStatusEnum.PENDING,
            "PROCESSING": JobStatusEnum.RUNNING,
            "COMPLETED": JobStatusEnum.SUCCESS,
            "FAILED": JobStatusEnum.FAILED,
            "CANCELLED": JobStatusEnum.FAILED,
        }
        result_items = []
        for item in (row.get("result") or []):
            sequence_target = item.get("sequence_target") or item.get("target_sequence")
            if not sequence_target:
                continue
            result_items.append(
                PredictionResultItem(
                    affinity=float(item["affinity"]),
                    target_sequence=str(sequence_target),
                )
            )
        return PredictionJob(
            id=UUID(str(row["id"])),
            smiles=Smiles(str(payload["smiles"])),
            dataset=Dataset(str(payload["dataset"])),
            options=Options(
                top_k=int(payload["top_k"]),
                return_sequence=bool(payload["return_sequence"]),
            ),
            model_version=ModelVersion(str(payload["model_version"])),
            status=JobStatus(reverse_status_map[str(row["status"])]),
            result=result_items,
            error=row.get("error_message"),
            created_at=_as_datetime(row["created_at"]),
            updated_at=_as_datetime(row["updated_at"]),
        )


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError(f"Expected datetime value, got {type(value)!r}")
