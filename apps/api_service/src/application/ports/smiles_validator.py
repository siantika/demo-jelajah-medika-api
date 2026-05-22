from __future__ import annotations

from typing import Protocol


class ISmilesValidator(Protocol):
    def is_valid(self, *, smiles: str) -> bool: ...
