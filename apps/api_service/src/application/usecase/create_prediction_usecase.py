from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
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
        if not self.smiles_validator.is_valid(smiles=cmd.smiles):
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES is not chemically valid",
                value=cmd.smiles,
            )

        options_cmd = cmd.options or PredictionOptionsCmd()
        request_hash = _build_request_hash(cmd=cmd, options_cmd=options_cmd)
        deterministic_job_id = uuid5(NAMESPACE_URL, request_hash)

        # ini harusnya redis
        # existing_job = self.repository.get_by_id(job_id=deterministic_job_id)
        # if existing_job is not None:
        #     return CreatePredictionResult(job_id=existing_job.id, task_id=str(existing_job.id))

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

        self.repository.create(job=prediction_job)
        task_id = self.job_queue.enqueue_prediction(job_id=prediction_job.id)
        return CreatePredictionResult(job_id=prediction_job.id, task_id=task_id)

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
        return CreatePredictionResult(job_id=prediction_job.id, task_id=task_id)


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
