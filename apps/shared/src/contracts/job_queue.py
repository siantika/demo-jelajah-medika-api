from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from apps.shared.src.contracts.messages import PredictionRequestedMessage


class PredictionJobQueueProducer(Protocol):
    def publish_prediction_requested(self, message: PredictionRequestedMessage) -> str: ...


@dataclass(frozen=True)
class ConsumedPredictionMessage:
    receipt_id: str
    message: PredictionRequestedMessage


class PredictionJobQueueConsumer(Protocol):
    def consume_prediction_requested(self, *, block_timeout_ms: int = 1000) -> ConsumedPredictionMessage | None: ...

    def ack(self, *, receipt_id: str) -> None: ...

    def nack(self, *, receipt_id: str, requeue: bool = True) -> None: ...
