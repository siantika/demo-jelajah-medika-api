import http from "k6/http";
import { check } from "k6";

const testType = __ENV.TEST_TYPE || "submit";
const baseUrl = (__ENV.BASE_URL || "http://localhost:18000").replace(/\/$/, "");
const vus = Number(__ENV.VUS || 20);
const duration = __ENV.DURATION || "30s";
const p95LimitMs = Number(__ENV.P95_LIMIT_MS || (testType === "submit" ? 1000 : 500));
const runId = (__ENV.K6_RUN_ID || `${Date.now()}`).replace(/[^A-Za-z0-9_.-]/g, "-");

if (!["health", "queue", "submit"].includes(testType)) {
  throw new Error(`TEST_TYPE must be health, queue, or submit; received: ${testType}`);
}

export const options = {
  vus,
  duration,
  discardResponseBodies: true,
  thresholds: {
    checks: ["rate>0.99"],
    http_req_failed: ["rate<0.01"],
    http_req_duration: [`p(95)<${p95LimitMs}`],
  },
  tags: {
    test_type: testType,
  },
};

const jsonHeaders = {
  headers: { "Content-Type": "application/json" },
  tags: { endpoint: "POST /api/v1/predictions" },
};

function testHealth() {
  const response = http.get(`${baseUrl}/health/db`, {
    tags: { endpoint: "GET /health/db" },
  });

  check(response, {
    "health returns 200": (res) => res.status === 200,
  });
}

function testQueueMetrics() {
  const response = http.get(`${baseUrl}/api/v1/queues/metrics`, {
    tags: { endpoint: "GET /api/v1/queues/metrics" },
  });

  check(response, {
    "queue metrics returns 200": (res) => res.status === 200,
  });
}

function testSubmission() {
  // model_version is deliberately unique. The API derives the job ID from the
  // request, so a fixed payload would only benchmark its idempotent read path.
  const uniqueModelVersion = `perf-${runId}-${__VU}-${__ITER}`.slice(0, 64);
  const payload = JSON.stringify({
    smiles: "CCO",
    dataset_name: "davis",
    model_version: uniqueModelVersion,
    options: {
      top_k: 5,
      return_sequences: false,
    },
  });

  const response = http.post(`${baseUrl}/api/v1/predictions`, payload, jsonHeaders);

  check(response, {
    "submission returns 202": (res) => res.status === 202,
  });
}

export default function () {
  if (testType === "health") {
    testHealth();
    return;
  }

  if (testType === "queue") {
    testQueueMetrics();
    return;
  }

  testSubmission();
}
