# Worker Runbook

## Purpose
Menjalankan ML queue consumer di production/development.

## Entry Point
```bash
python -m apps.ml_engine_service.src.worker.queue_worker
```

## Required Configuration
- `DATABASE_URL`

## Optional Configuration
- `REDIS_URL` (default `redis://localhost:6379/0`)
- `ML_QUEUE_KEY` (default `queue:ml:queued`)
- `REDIS_QUEUE_KEY` (fallback alias)
- `ML_WORKER_ON_ERROR` (`requeue` or `dlq`, default `requeue`)
- `ML_MAX_RETRIES` (default `3`)
- `ML_WORKER_POLL_INTERVAL` (default `1`)
- `ML_ASSETS_ROOT` (default `.`)
- `ML_GNN_FEATURES` (default `40`)
- `ML_GNN_DEPTH` (default `3`)
- `ML_MLP_DEPTH` (default `2`)

## Health Checks
- Process hidup dan log startup keluar.
- Queue depth wajar (`queued/retry/dlq`).
- Job status di DB bergerak (`PENDING -> RUNNING -> SUCCESS/FAILED`).

## Common Failures
### DB auth error
Gejala: `password authentication failed`.
Aksi: validasi `DATABASE_URL` yang aktif di process env.

### Model mismatch
Gejala: `size mismatch / unexpected keys in state_dict`.
Aksi: sinkronkan `ML_GNN_FEATURES`, `ML_GNN_DEPTH`, `ML_MLP_DEPTH` dengan checkpoint.

### Infinite retry loop
Gejala: log gagal berulang tanpa DLQ.
Aksi: pastikan `ML_MAX_RETRIES` diset dan `ML_WORKER_ON_ERROR=requeue` sesuai kebutuhan.

## Operational Commands
Lihat queue length (contoh default keys):
```bash
redis-cli LLEN queue:ml:queued
redis-cli LLEN queue:ml:processing
redis-cli LLEN queue:ml:retry
redis-cli LLEN queue:ml:dlq
```

