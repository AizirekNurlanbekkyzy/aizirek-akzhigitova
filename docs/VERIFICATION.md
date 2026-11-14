# Verification record

This file records commands actually run in the current Windows environment. A successful local SQLite run is not evidence of PostgreSQL or Docker integration.

## Results

| Area | Command or scenario | Result |
|---|---|---|
| Backend lint | `uv run ruff check app tests alembic` | Passed |
| Backend formatting | `uv run ruff format --check app tests alembic` | Passed |
| Backend types | `uv run ty check app alembic` | Passed |
| Backend API and domain tests | `uv run pytest -q` with SQLite in-memory and test secrets | 16 passed; pytest-asyncio emits Python 3.14 deprecation warnings |
| Seed repeatability | `tests/test_seed.py` | Passed: first call added 98 rows, second added 0; expected tenants/users/requests/technicians/assets/estimates/inventory counts verified |
| Production seed guard | `tests/test_seed.py` | Passed: seed rejects `APP_ENV=production` |
| PostgreSQL migration SQL | `uv run python -m alembic upgrade head --sql` with PostgreSQL dialect and placeholder local verification URL | Passed; SQL generated offline, no PostgreSQL server was contacted |
| Web dependency lock | `pnpm install --lockfile-only --no-frozen-lockfile --store-dir .pnpm-store` | Passed; generated `pnpm-lock.yaml` |
| Web install | `pnpm install --frozen-lockfile` | Not runnable in this restricted session: pnpm's project registration attempts a Windows symlink into the managed pnpm cache and receives EPERM. Dependencies were installed with hoisted/copy flags for local verification. |
| Web TypeScript | `node node_modules/typescript/bin/tsc --noEmit` | Passed |
| Web production build | `node node_modules/next/dist/bin/next build` | Passed; Next.js 16.4.6 generated the production build |
| Web API-client unit test | `bun test` | 1 passed |
| Live web-to-API smoke | Next on `localhost:3000`, FastAPI on `localhost:8123`, SQLite seed database | Passed: customer logged in and dashboard loaded 25 real seeded requests from API |
| API health/CORS/OpenAPI | live FastAPI on SQLite | Passed: liveness, readiness, OpenAPI, and CORS preflight |
| Compose configuration | `docker compose config --quiet` | Passed |
| Docker Engine | `docker info --format '{{.ServerVersion}}'` | Failed: access denied for `npipe:////./pipe/dockerDesktopLinuxEngine` |
| Docker build/start/restart | `docker compose up --build` | Not run: Docker Engine pipe is inaccessible |
| PostgreSQL migrations/seed/persistence | Container scenario | Not run: no container engine; data-volume behavior and PostgreSQL locking remain unverified |
| Android build | Flutter commands | Not run: Flutter/Android build toolchain is unavailable |

The temporary browser smoke used a local SQLite file inside the ignored backend cache and demo-only data. It did not use PostgreSQL. The browser and API smoke servers were stopped after verification.
