from dataclasses import dataclass
from enum import Enum

from apps.shared.job_management.domain.exceptions import InvalidValueObject


class JobStatusEnum(str, Enum):
    PENDING: str = "PENDING"
    RUNNING: str = "RUNNING"
    SUCCESS: str = "SUCCESS"
    FAILED: str = "FAILED"  
    

@dataclass(frozen=True)
class JobStatus:
    value: JobStatusEnum
    
    def __post_init__(self) -> None:
        # Ensure value is not None or empty
        if self.value is None or str(self.value).strip() == "":
            raise InvalidValueObject(
                name="JobStatus",
                reason="JobStatus cannot be None or empty",
                value=self.value
            )
        # Ensure value is a valid JobStatusEnum
        if not isinstance(self.value, JobStatusEnum):
            raise InvalidValueObject(
                name="JobStatus",
                reason="JobStatus should be JobStatusEnumType",
                value=self.value
            )

    def __str__(self) -> str:
        return self.value.value
