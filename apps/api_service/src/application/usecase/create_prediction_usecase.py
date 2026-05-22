from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from apps.api_service.src.application.dto import (
    CreatePredictionCmd,
    PredictionOptionsCmd,
)
from apps.api_service.src.application.ports.job_queue import JobQueue
from apps.api_service.src.application.ports.prediction_job_repository import (
    PredictionJobRepository,
)
from apps.api_service.src.application.ports.smiles_validator import SmilesValidator
from apps.shared.domain.entities.prediction_job import (
    PredictionJob,
)
from apps.shared.domain.exceptions import InvalidValueObject
from apps.shared.domain.value_objects.dataset import Dataset
from apps.shared.domain.value_objects.model_version import (
    ModelVersion,
)
from apps.shared.domain.value_objects.options import Options
from apps.shared.domain.value_objects.smiles import Smiles


@dataclass(frozen=True)
class CreatePredictionResult:
    job_id: UUID
    task_id: str
    created_at: datetime


class CreatePredictionJobUseCase:
    def __init__(
        self,
        job_queue: JobQueue,
        smiles_validator: SmilesValidator,
        repository: PredictionJobRepository,
    ):
        self.job_queue = job_queue
        self.smiles_validator = smiles_validator
        self.repository = repository

    def execute(self, cmd: CreatePredictionCmd) -> CreatePredictionResult:
        # validate smiles input 
        if not self.smiles_validator.is_valid(smiles=cmd.smiles):
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES is not chemically valid",
                value=cmd.smiles,
            )

        # create value object for options field
        options_cmd = cmd.options or PredictionOptionsCmd()
        
        # It uses for idempotency resquest for same request
        request_hash = _build_request_hash(cmd=cmd, options_cmd=options_cmd)
        deterministic_job_id = uuid5(NAMESPACE_URL, request_hash)

        # job should not process the same request
        existing_job = self.repository.get_by_id(job_id=deterministic_job_id)
        if existing_job is not None:
            return CreatePredictionResult(
                job_id=existing_job.id,
                task_id=str(existing_job.id),
                created_at=existing_job.created_at,
            )
        
        # Create prediction Entity of prediction job
        prediction_job = PredictionJob(
            id=deterministic_job_id,
            smiles=Smiles(cmd.smiles),
            dataset=Dataset(cmd.dataset_name),
            options=Options(
                top_k=options_cmd.top_k,
                return_sequence=options_cmd.return_sequences,
            ),
            model_version=ModelVersion(cmd.model_version),
        )

        # create and save prediction job to persitent layer
        self.repository.create(job=prediction_job)
        
        # Produce job_id to queue. Let another service consume it
        task_id = self.job_queue.enqueue_prediction(job_id=prediction_job.id)
        
        # return result
        return CreatePredictionResult(
            job_id=prediction_job.id,
            task_id=task_id,
            created_at=prediction_job.created_at,
        )

    async def execute_async(self, cmd: CreatePredictionCmd) -> CreatePredictionResult:
        if not self.smiles_validator.is_valid(smiles=cmd.smiles):
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES is not chemically valid",
                value=cmd.smiles,
            )

        options_cmd = cmd.options or PredictionOptionsCmd()
        request_hash = _build_request_hash(cmd=cmd, options_cmd=options_cmd)
        deterministic_job_id = uuid5(NAMESPACE_URL, request_hash)
        existing_job_result = self.repository.get_by_id(job_id=deterministic_job_id)
        existing_job = await existing_job_result if inspect.isawaitable(existing_job_result) else existing_job_result
        if existing_job is not None:
            return CreatePredictionResult(
                job_id=existing_job.id,
                task_id=str(existing_job.id),
                created_at=existing_job.created_at,
            )

        prediction_job = PredictionJob(
            id=deterministic_job_id,
            smiles=Smiles(cmd.smiles),
            dataset=Dataset(cmd.dataset_name),
            options=Options(
                top_k=options_cmd.top_k,
                return_sequence=options_cmd.return_sequences,
            ),
            model_version=ModelVersion(cmd.model_version),
        )

        create_result = self.repository.create(job=prediction_job)
        if inspect.isawaitable(create_result):
            await create_result

        task_id_result = self.job_queue.enqueue_prediction(job_id=prediction_job.id)
        task_id = await task_id_result if inspect.isawaitable(task_id_result) else task_id_result
        return CreatePredictionResult(
            job_id=prediction_job.id,
            task_id=task_id,
            created_at=prediction_job.created_at,
        )


def _build_request_hash(*, cmd: CreatePredictionCmd, options_cmd: PredictionOptionsCmd) -> str:
    canonical_payload = {
        "smiles": cmd.smiles.strip(),
        "dataset_name": cmd.dataset_name,
        "model_version": cmd.model_version,
        "options": {
            "top_k": options_cmd.top_k,
            "return_sequences": options_cmd.return_sequences,
        },
    }
    serialized = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
