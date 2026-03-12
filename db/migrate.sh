#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${1:-infra/docker-compose.yml}"

for file in db/migrations/*.sql; do
  if [ ! -f "$file" ]; then
    continue
  fi

  base_name="$(basename "$file")"
  echo "Applying migration: $base_name"
  docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U user -d hiring_system -v ON_ERROR_STOP=1 -f "/migrations/$base_name"
done
