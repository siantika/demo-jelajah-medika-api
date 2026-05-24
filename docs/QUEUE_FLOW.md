# Queue Flow

## Queue Keys
Didefinisikan di `apps/shared/queues.py`:
- `queue:ml:queued`
- `queue:ml:processing`
- `queue:ml:retry`
- `queue:ml:dlq`

## Producer Flow (API)
- Adapter: `apps/api_service/src/infra/queue/redis_job_queue.py`
- Method: `enqueue_prediction(job_id=...)`
- Action: push `job_id` ke queue queued.

## Consumer Flow (ML Worker)
- Adapter: `apps/ml_engine_service/src/infra/queue/redis_queue_job.py`
- Runtime: `apps/ml_engine_service/src/worker/queue_worker.py`

Loop per tick:
1. `promote_retry()` memindahkan satu job dari retry ke queued.
2. `dequeue()` memindahkan satu job dari queued ke processing.
3. Worker proses job via `RunPredictionJobUseCase`.

## Success Path
1. `clear_retry_count(job_id)`
2. `ack(job_id)` -> remove from processing

## Failure Path (`ML_WORKER_ON_ERROR=dlq`)
1. `move_to_dlq(job_id)`
2. `clear_retry_count(job_id)`

## Failure Path (`ML_WORKER_ON_ERROR=requeue`)
1. `increment_retry_count(job_id)`
2. Jika `retry_count > ML_MAX_RETRIES`: move to DLQ
3. Jika masih <= batas: `requeue(job_id)` -> push ke retry queue

## Retry Counter
- Disimpan di Redis hash key: `<queued_key>:retry_count`
- Counter dibersihkan saat success atau masuk DLQ

