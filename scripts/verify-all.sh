#!/usr/bin/env sh
set -eu
(cd backend && uv sync --frozen && uv run ruff check . && uv run ruff format --check . && uv run ty check . && uv run pytest -q)
(cd web && bun install --frozen-lockfile && bun run lint && bun run typecheck && bun run test:ci && bun run build)
(cd mobile && flutter pub get && dart format --output=none --set-exit-if-changed lib test && flutter analyze && flutter test && flutter build apk --debug)
