from __future__ import annotations

from typing import Protocol


class IRepoQueue(Protocol):
    async def get_metrics(self) -> tuple[int, int, int, int]: ...
