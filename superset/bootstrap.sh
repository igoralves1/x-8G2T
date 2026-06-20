#!/usr/bin/env bash
# Initialise Superset (idempotent) and start the web server.
set -euo pipefail

echo ">> Upgrading Superset metadata DB..."
superset db upgrade

echo ">> Ensuring admin user..."
superset fab create-admin \
    --username "${ADMIN_USERNAME:-admin}" \
    --firstname Admin --lastname User \
    --email admin@x-8g2t.local \
    --password "${ADMIN_PASSWORD:-admin}" || true

echo ">> Running superset init..."
superset init

echo ">> Starting Superset..."
exec gunicorn \
    --bind 0.0.0.0:8088 \
    --workers 3 \
    --timeout 120 \
    "superset.app:create_app()"
