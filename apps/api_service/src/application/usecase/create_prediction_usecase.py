from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from apps.api_service.src.application.dto import (
    CreatePredictionCmd,
    PredictionOptionsCmd,
)
from apps.api_service.src.application.ports.job_queue import IJobQueue
from apps.api_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.api_service.src.application.ports.smiles_validator import ISmilesValidator
from apps.shared.src.domain.entities.prediction_job import (
    PredictionJob,
)
from apps.shared.src.domain.exceptions import InvalidValueObject
from apps.shared.src.domain.value_objects.dataset import Dataset
from apps.shared.src.domain.value_objects.model_version import (
    ModelVersion,
)
from apps.shared.src.domain.value_objects.options import Options
from apps.shared.src.domain.value_objects.smiles import Smiles


@dataclass(frozen=True)
class CreatePredictionResult:
    job_id: UUID
    task_id: str
    created_at: datetime


class CreatePredictionJobUseCase:
    def __init__(
        self,
        job_queue: IJobQueue,
        smiles_validator: ISmilesValidator,
        repository: IPredictionJobRepository
    ):
        self.job_queue = job_queue
        self.smiles_validator = smiles_validator
        self.repository = repository


    async def execute(self, cmd: CreatePredictionCmd) -> PredictionJob:
        # validate smiles input 
        if not self.smiles_validator.is_valid(smiles=cmd.smiles):
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES is not chemically valid",
                value=cmd.smiles,
            )

        # create value object for options field
        options_cmd = cmd.options or PredictionOptionsCmd()
        
        # Generate a deterministic job ID for idempotent duplicate requests.
        request_hash = _build_request_hash(cmd=cmd, options_cmd=options_cmd)
        deterministic_job_id = uuid5(NAMESPACE_URL, request_hash)

        # Should not process a request with a same job
        existing_job = await self.repository.find_by_id(job_id=deterministic_job_id)
        if existing_job is not None:
            return existing_job
        
        # Create prediction job entity
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
        await self.repository.save(job=prediction_job)
        
        # Send job_id to ML queue. Let another services consume it 
        await self.job_queue.enqueue_prediction(job_id=prediction_job.id)
        
        # return result
        return prediction_job

# For now, the implementation is acceptable here. Next, we can move it in infra layer and access using Interface located in ports folder
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
