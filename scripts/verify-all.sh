#!/usr/bin/env sh
set -eu
(cd backend && uv sync --frozen && uv run ruff check . && uv run ruff format --check . && uv run ty check app alembic && DATABASE_URL='sqlite+aiosqlite:///:memory:' JWT_SECRET='test-secret-for-fixflow-tests-only-000000000000000000' APP_ENV=test uv run pytest -q)
(cd web && pnpm install --frozen-lockfile && pnpm run typecheck && bun run test:ci && pnpm run build)
(cd mobile && flutter pub get && dart format --output=none --set-exit-if-changed lib test && flutter analyze && flutter test && flutter build apk --debug)
