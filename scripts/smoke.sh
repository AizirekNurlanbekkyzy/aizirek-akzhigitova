#!/usr/bin/env sh
set -eu
curl --fail http://localhost:${BACKEND_PORT:-8000}/health/live
curl --fail http://localhost:${BACKEND_PORT:-8000}/health/ready
curl --fail http://localhost:${BACKEND_PORT:-8000}/api/v1/openapi.json >/dev/null
curl --fail http://localhost:${WEB_PORT:-3000}/ >/dev/null
