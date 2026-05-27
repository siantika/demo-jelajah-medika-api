from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.src.contracts.prediction_job_repository import IPredictionJobRepository
from apps.shared.src.domain.entities.prediction_job import PredictionJob
from apps.shared.src.domain.value_objects.dataset import Dataset
from apps.shared.src.domain.value_objects.job_status import JobStatus, JobStatusEnum
from apps.shared.src.domain.value_objects.model_version import ModelVersion
from apps.shared.src.domain.value_objects.options import Options
from apps.shared.src.domain.value_objects.prediction_result_item import PredictionResultItem
from apps.shared.src.domain.value_objects.smiles import Smiles
from apps.shared.src.infra.db.models.jobs import jobs


class SQLAlchemyPredictionJobRepository(IPredictionJobRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._session = db

    async def save(self, *, job: PredictionJob) -> None:
        row = self._to_row(job)
        stmt = insert(jobs).values(**row).on_conflict_do_update(
            index_elements=[jobs.c.id],
            set_={
                "type": row["type"],
                "status": row["status"],
                "payload": row["payload"],
                "result": row["result"],
                "error_code": row["error_code"],
                "error_message": row["error_message"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "failed_at": row["failed_at"],
                "updated_at": row["updated_at"],
                "idempotency_key": row["idempotency_key"],
                "request_hash": row["request_hash"],
                "correlation_id": row["correlation_id"],
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def find_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        stmt = select(jobs).where(jobs.c.id == job_id)
        row = (await self._session.execute(stmt)).mappings().first()
        return self._from_row(dict(row)) if row is not None else None

    async def mark_retry_scheduled(
        self,
        *,
        job_id: UUID,
        next_retry_at: datetime,
        retry_count: int,
    ) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(jobs)
            .where(jobs.c.id == job_id)
            .values(
                status="RETRY_SCHEDULED",
                retry_count=retry_count,
                next_retry_at=next_retry_at,
                updated_at=now,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def mark_queued(
        self,
        *,
        job_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(jobs)
            .where(jobs.c.id == job_id)
            .values(
                status="QUEUED",
                next_retry_at=None,
                updated_at=now,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    @staticmethod
    def _to_row(job: PredictionJob) -> dict:
        status_map = {
            JobStatusEnum.PENDING: "QUEUED",
            JobStatusEnum.RUNNING: "PROCESSING",
            JobStatusEnum.SUCCESS: "COMPLETED",
            JobStatusEnum.FAILED: "FAILED",
        }
        db_status = status_map[job.status.value]
        return {
            "id": job.id,
            "type": "prediction",
            "status": db_status,
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
            "error_code": None,
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
            "started_at": job.updated_at if db_status == "PROCESSING" else None,
            "completed_at": job.updated_at if db_status == "COMPLETED" else None,
            "failed_at": job.updated_at if db_status == "FAILED" else None,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    @staticmethod
    def _from_row(row: dict) -> PredictionJob:
        payload = row.get("payload") or {}
        reverse_status_map = {
            "QUEUED": JobStatusEnum.PENDING,
            "PROCESSING": JobStatusEnum.RUNNING,
            "RETRY_SCHEDULED": JobStatusEnum.RUNNING,
            "COMPLETED": JobStatusEnum.SUCCESS,
            "DEAD": JobStatusEnum.FAILED,
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
