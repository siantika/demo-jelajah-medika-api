# API load test

This directory contains repeatable k6 tests for the asynchronous prediction API.

## What is measured

- `health`: database-backed API latency and maximum request throughput.
- `queue`: Redis-backed queue-metrics latency and maximum request throughput.
- `submit`: durable job-acceptance latency and throughput through PostgreSQL and Redis.

The `submit` case sends a unique `model_version` for every request. This avoids the
idempotent duplicate-request path and ensures every successful request writes a
new database row and enqueues a new job.

These tests measure API acceptance (`202 Accepted`), not ML inference completion.
Worker throughput should be measured separately from job creation because it is
an asynchronous consumer with a different capacity limit.

## Run

Start the application, then run all cases:

```bash
./test-result/run-load-test.sh all
```

Run one case or change the load:

```bash
VUS=50 DURATION=60s BASE_URL=http://localhost:18000 \
  ./test-result/run-load-test.sh submit
```

Optional `P95_LIMIT_MS` changes the pass/fail threshold. Its default is 500 ms
for read endpoints and 1000 ms for submissions.

Each run writes a k6 summary, console output, and execution metadata under
`test-result/results/`. A submission run creates database records and queue
entries, so use an isolated performance-test environment when possible.
