import re
from dataclasses import dataclass

from apps.shared.job_management_domain.domain.exceptions import InvalidValueObject

_MODEL_VERSION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

@dataclass(frozen=True)
class ModelVersion:
    value: str

    def __post_init__(self):
        raw = self.value
        if raw is None:
            raise InvalidValueObject(
                name="ModelVersion",
                reason="Model version cannot be None",
                value=raw
            )
        s = raw.strip()
        if not s:
            raise InvalidValueObject(
                name="ModelVersion",
                reason="Model version cannot be empty",
                value=raw
            )
        if len(s) > 64:
            raise InvalidValueObject(
                name="ModelVersion",
                reason="Model version is too long (max 64 characters)",
                value=s
            )
        if not _MODEL_VERSION_RE.match(s):
            raise InvalidValueObject(
                name="ModelVersion",
                reason="Model version contains invalid characters (allowed: A-Z, a-z, 0-9, _, ., -)",
                value=s
            )
        object.__setattr__(self, "value", s)

    def __str__(self) -> str:
        return self.value
