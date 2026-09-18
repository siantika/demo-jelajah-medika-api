#!/usr/bin/env bash
set -euo pipefail

TEST_RESULT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOAD_TEST_SCRIPT="${TEST_RESULT_DIR}/load-test.js"
RESULT_DIR="${TEST_RESULT_DIR}/results"

BASE_URL="${BASE_URL:-http://localhost:18000}"
VUS="${VUS:-20}"
DURATION="${DURATION:-30s}"
TEST_TYPE="${1:-all}"
RUN_TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if ! command -v k6 >/dev/null 2>&1; then
  echo "k6 is required: https://grafana.com/docs/k6/latest/set-up/install-k6/" >&2
  exit 1
fi

case "${TEST_TYPE}" in
  all)
    TEST_CASES=(health queue submit)
    ;;
  health|queue|submit)
    TEST_CASES=("${TEST_TYPE}")
    ;;
  *)
    echo "Usage: $0 [all|health|queue|submit]" >&2
    exit 2
    ;;
esac

mkdir -p "${RESULT_DIR}"

run_case() {
  local test_case="$1"
  local p95_limit_ms="${P95_LIMIT_MS:-500}"
  local result_prefix="${RESULT_DIR}/${RUN_TIMESTAMP}-${test_case}"

  if [[ "${test_case}" == "submit" && -z "${P95_LIMIT_MS:-}" ]]; then
    p95_limit_ms=1000
  fi

  {
    echo "test_type=${test_case}"
    echo "base_url=${BASE_URL}"
    echo "vus=${VUS}"
    echo "duration=${DURATION}"
    echo "p95_limit_ms=${p95_limit_ms}"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "k6_version=$(k6 version | head -n 1)"
  } > "${result_prefix}-metadata.txt"

  echo "Running ${test_case}: ${VUS} VUs for ${DURATION} against ${BASE_URL}"
  BASE_URL="${BASE_URL}" \
    VUS="${VUS}" \
    DURATION="${DURATION}" \
    TEST_TYPE="${test_case}" \
    P95_LIMIT_MS="${p95_limit_ms}" \
    K6_RUN_ID="${RUN_TIMESTAMP}-${test_case}" \
    k6 run \
      --summary-export "${result_prefix}-summary.json" \
      "${LOAD_TEST_SCRIPT}" \
      2>&1 | tee "${result_prefix}-console.txt"
}

for test_case in "${TEST_CASES[@]}"; do
  run_case "${test_case}"
done

echo "Results written to ${RESULT_DIR}"
