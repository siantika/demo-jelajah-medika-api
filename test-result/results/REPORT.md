# Load-test report

Test time: 2026-09-18 04:12-04:14 UTC (11:12-11:14 Asia/Jakarta)

## Test environment

- API: one Uvicorn worker, access log disabled, bound to `127.0.0.1:18000`
- Load generator: k6 v2.2.0 on the same host
- Load: 20 virtual users for 20 seconds per scenario
- PostgreSQL 16 and Redis 7 ran in isolated local containers
- Thresholds: error rate below 1%; p95 below 500 ms for reads and 1000 ms for submission

## Results

| Scenario | Requests | Throughput | Average | Median | p95 | Maximum | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| `GET /health/db` | 24,472 | 1,223.05 req/s | 16.26 ms | 12.94 ms | 30.90 ms | 233.51 ms | 0% |
| `GET /api/v1/queues/metrics` | 13,697 | 684.16 req/s | 29.15 ms | 28.05 ms | 35.70 ms | 88.58 ms | 0% |
| `POST /api/v1/predictions` | 3,705 | 184.68 req/s | 108.02 ms | 98.14 ms | 193.24 ms | 306.28 ms | 0% |

All scenarios passed their latency, check-rate, and HTTP-error thresholds.

The submission test uses a unique payload per request, so it exercises the full
job-acceptance path: validation, PostgreSQL lookup/write, and Redis enqueue. A
post-test integrity check found 3,706 `QUEUED` rows and 3,706 Redis queue items;
this consists of 3,705 load-test jobs plus one pre-test smoke-test job.

## Interpretation

Under this single-process local configuration, the API accepted approximately
185 new asynchronous jobs per second while keeping p95 acceptance latency below
200 ms. This is API ingress capacity, not ML inference throughput. Because no ML
worker was active during this isolated test, it does not establish how quickly
queued jobs can be completed or whether the worker can sustain the same rate.

The raw k6 summaries, console output, and run metadata are stored beside this
report. Results from another machine or from multiple Uvicorn workers should not
be compared without recording those configuration differences.
