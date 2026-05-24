from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from apps.api_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.shared.src.domain.entities.prediction_job import (
    PredictionJob,
)
from apps.shared.src.domain.value_objects.dataset import Dataset
from apps.shared.src.domain.value_objects.job_status import (
    JobStatus,
    JobStatusEnum,
)
from apps.shared.src.domain.value_objects.model_version import (
    ModelVersion,
)
from apps.shared.src.domain.value_objects.options import Options
from apps.shared.src.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.src.domain.value_objects.smiles import Smiles
from apps.shared.src.infra.db.models.jobs import jobs


class SQLAlchemyPredictionJobRepository(IPredictionJobRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._session = db

    async def save(self, *, job: PredictionJob) -> None:
        """Persist a new PredictionJob.  Raises IntegrityError on duplicate id."""
        stmt = (
            insert(jobs)
            .values(**self._to_row(job))
            .on_conflict_do_nothing(index_elements=[jobs.c.id])
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def find_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        """Return the job with the given id, or None if not found."""
        stmt = select(jobs).where(jobs.c.id == job_id)
        row = (await self._session.execute(stmt)).mappings().first()
        return self._from_row(dict(row)) if row is not None else None


    @staticmethod
    def _to_row(job: PredictionJob) -> dict:
        status_map = {
            JobStatusEnum.PENDING: "QUEUED",
            JobStatusEnum.RUNNING: "PROCESSING",
            JobStatusEnum.SUCCESS: "COMPLETED",
            JobStatusEnum.FAILED: "FAILED",
        }
        return {
            "id": job.id,
            "type": "prediction",
            "status": status_map[job.status.value],
            "payload": {
                "smiles": str(job.smiles),
                "dataset": str(job.dataset),
                "top_k": job.options.top_k,
                "return_sequence": job.options.return_sequence,
                "model_version": str(job.model_version),
            },
            "result": [
                {
                    "affinity": item.affinity,
                    "sequence_target": item.target_sequence,
                    "target_index": None,
                }
                for item in job.result
            ],
            "error_message": job.error,
            "idempotency_key": str(job.id),
            "request_hash": _build_request_hash(
                smiles=str(job.smiles),
                dataset=str(job.dataset),
                top_k=job.options.top_k,
                return_sequence=job.options.return_sequence,
                model_version=str(job.model_version),
            ),
            "correlation_id": str(job.id),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

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
    raise TypeError(f"Expected datetime, got {type(value)!r}")


def _build_request_hash(
    *,
    smiles: str,
    dataset: str,
    top_k: int,
    return_sequence: bool,
    model_version: str,
) -> str:
    payload = {
        "smiles": smiles.strip(),
        "dataset_name": dataset,
        "model_version": model_version,
        "options": {
            "top_k": top_k,
            "return_sequences": return_sequence,
        },
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
