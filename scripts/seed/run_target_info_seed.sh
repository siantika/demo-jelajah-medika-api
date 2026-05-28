#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEED_FILE="${SEED_FILE:-$ROOT_DIR/scripts/seed/target_info_seed.sql}"
MODE="${1:-host}"

if [[ ! -f "$SEED_FILE" ]]; then
  echo "Seed file not found: $SEED_FILE" >&2
  exit 1
fi

case "$MODE" in
  host)
    : "${DATABASE_URL:?DATABASE_URL is required for host mode}"
    echo "Seeding target_info to host DB using DATABASE_URL"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$SEED_FILE"
    ;;
  docker)
    COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker/docker-compose.dev.yml}"
    DB_SERVICE="${DB_SERVICE:-db}"
    : "${POSTGRES_USER:?POSTGRES_USER is required for docker mode}"
    : "${POSTGRES_DB:?POSTGRES_DB is required for docker mode}"
    echo "Seeding target_info to docker service '$DB_SERVICE' via $COMPOSE_FILE"
    docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
      < "$SEED_FILE"
    ;;
  *)
    echo "Usage: $0 [host|docker]" >&2
    exit 1
    ;;
esac

echo "Seed completed: $SEED_FILE"
