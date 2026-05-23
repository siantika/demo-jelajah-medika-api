from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RunPredictionJobCmd:
    job_id: UUID
