# Architecture V2 (Current Repo)

## Scope
Dokumen ini menjelaskan arsitektur modular yang sekarang dipakai di repository `demo-api-jelajah-medika`.

## Components
- `apps/api_service`: FastAPI producer (create job + enqueue).
- `apps/ml_engine_service`: background consumer worker (dequeue + predict + update status).
- `apps/shared`: domain model, contracts, database table metadata, queue constants.
- `PostgreSQL`: persistent job state.
- `Redis`: transport queue (`queued`, `processing`, `retry`, `dlq`).

## Boundaries
- API service tidak mengimpor modul internal ML service.
- ML service tidak mengimpor modul internal API service.
- Keduanya berbagi contract/domain via `apps/shared`.

## Job Lifecycle
1. API menerima request prediksi.
2. API simpan `PredictionJob` ke DB (status awal `PENDING`).
3. API enqueue `job_id` ke `queue:ml:queued`.
4. Worker ML consume queue dan jalankan inference.
5. Sukses: status `SUCCESS`, queue `ack`.
6. Gagal: status `FAILED`, lalu retry flow (`retry`/`dlq`) sesuai policy.

## Source of Truth
- Domain: `apps/shared/domain`
- Queue constants: `apps/shared/queues.py`
- DB table metadata: `apps/shared/infra/db/models`
- API use cases: `apps/api_service/src/application/usecase`
- Worker runtime: `apps/ml_engine_service/src/worker/queue_worker.py`

## Runtime Entry Points
- API: `apps.api_service.src.main:app`
- Worker: `python -m apps.ml_engine_service.src.worker.queue_worker`

