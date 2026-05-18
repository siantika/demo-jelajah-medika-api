from dataclasses import dataclass

from apps.shared.job_management.domain.exceptions import InvalidValueObject


@dataclass(frozen=True)
class Options:
    top_k: int
    return_sequence: bool

    def __post_init__(self):
        if not isinstance(self.top_k, int) or self.top_k <= 0:
            raise InvalidValueObject(
                name="Options.top_k",
                reason=f"top_k must be a positive integer, got {self.top_k}",
                value=self.top_k)
        if not isinstance(self.return_sequence, bool):
            raise InvalidValueObject(
                name="Options.return_sequence",
                reason=f"return_sequence must be a boolean, got {self.return_sequence}",
                value=self.return_sequence)
    