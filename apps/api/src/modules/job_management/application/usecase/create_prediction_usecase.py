from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from modules.job_management.application.dto import CreatePredictionCmd, PredictionOptionsCmd
from modules.job_management.application.ports.job_queue import JobQueue
from modules.job_management.application.ports.smiles_validator import SmilesValidator
from modules.job_management.domain.entities.prediction_job import PredictionJob
from modules.job_management.domain.exceptions import InvalidValueObject
from modules.job_management.domain.value_objects.dataset import Dataset
from modules.job_management.domain.value_objects.model_version import ModelVersion
from modules.job_management.domain.value_objects.options import Options
from modules.job_management.domain.value_objects.smiles import Smiles


@dataclass(frozen=True)
class CreatePredictionResult:
    prediction_id: UUID
    task_id: str


class CreatePredictionJobUseCase:
    def __init__(self, job_queue: JobQueue, smiles_validator: SmilesValidator):
        self.job_queue = job_queue
        self.smiles_validator = smiles_validator

    def execute(self, cmd: CreatePredictionCmd) -> CreatePredictionResult:
        if not self.smiles_validator.is_valid(smiles=cmd.smiles):
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES is not chemically valid",
                value=cmd.smiles,
            )

        options_cmd = cmd.options or PredictionOptionsCmd()

        prediction_job = PredictionJob(
            id=uuid4(),
            smiles=Smiles(cmd.smiles),
            dataset=Dataset(cmd.dataset_name),
            options=Options(
                top_k=options_cmd.top_k,
                return_sequence=options_cmd.return_sequences,
            ),
            model_version=ModelVersion(cmd.model_version),
        )

        task_id = self.job_queue.enqueue_prediction(prediction_id=prediction_job.id)
        return CreatePredictionResult(prediction_id=prediction_job.id, task_id=task_id)
