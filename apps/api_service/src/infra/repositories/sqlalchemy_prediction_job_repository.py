from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.api_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.api_service.src.shared.database.engine import engine as shared_engine
from apps.api_service.src.shared.database.session import (
    SessionFactory as shared_session_factory,
)
from apps.api_service.src.shared.settings.config import settings
from apps.shared.domain.entities.prediction_job import (
    PredictionJob,
)
from apps.shared.domain.value_objects.dataset import Dataset
from apps.shared.domain.value_objects.job_status import (
    JobStatus,
    JobStatusEnum,
)
from apps.shared.domain.value_objects.model_version import (
    ModelVersion,
)
from apps.shared.domain.value_objects.options import Options
from apps.shared.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.domain.value_objects.smiles import Smiles
from apps.shared.infra.db.models.jobs import jobs


class SQLAlchemyPredictionJobRepository(IPredictionJobRepository):
    """
    Async SQLAlchemy implementation of PredictionJobRepository.

    Lifecycle
    ---------
    The engine and connection pool are created once in __init__ and shared
    across all operations.  Call ``await repo.dispose()`` (e.g. in an app
    shutdown / lifespan handler) to cleanly close the pool.

    Usage with FastAPI lifespan
    ---------------------------
    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repo = SQLAlchemyPredictionJobRepository()
        app.state.repo = repo
        yield
        await repo.dispose()
    ```
    """

    def __init__(self, database_url: str | None = None) -> None:
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is required for SQLAlchemyPredictionJobRepository")
        if url == settings.database_url:
            self._engine = shared_engine
            self._session_factory = shared_session_factory
            self._owns_engine = False
            return

        self._engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        self._owns_engine = True

    # ------------------------------------------------------------------
    # Public interface (fully async)
    # ------------------------------------------------------------------

    async def create(self, *, job: PredictionJob) -> None:
        """Persist a new PredictionJob.  Raises IntegrityError on duplicate id."""
        stmt = (
            insert(jobs)
            .values(**self._to_row(job))
            .on_conflict_do_nothing(index_elements=[jobs.c.id])
        )
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        """Return the job with the given id, or None if not found."""
        stmt = select(jobs).where(jobs.c.id == job_id)
        async with self._session_factory() as session:
            row = (await session.execute(stmt)).mappings().first()
        return self._from_row(dict(row)) if row is not None else None

    async def update_status(
        self,
        *,
        job_id: UUID,
        status: JobStatus,
        result: list[PredictionResultItem] | None = None,
        error: str | None = None,
        updated_at: datetime,
    ) -> None:
        """Update status (and optionally result / error) for an existing job."""
        values: dict = {
            "status": status.value.value,
            "updated_at": updated_at,
        }
        if result is not None:
            values["result"] = [
                {
                    "affinity": item.affinity,
                    "sequence_target": item.target_sequence,
                    "target_index": None,
                }
                for item in result
            ]
        if error is not None:
            values["error_message"] = error
            values["error_code"] = "PREDICTION_FAILED"

        stmt = (
            update(jobs)
            .where(jobs.c.id == job_id)
            .values(**values)
        )
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def dispose(self) -> None:
        """Dispose the connection pool.  Call once at application shutdown."""
        if self._owns_engine:
            await self._engine.dispose()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
