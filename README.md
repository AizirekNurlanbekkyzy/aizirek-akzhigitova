# FixFlow — Aizirek Akzhigitova

FixFlow is intended to connect customer service requests, dispatch, and field work through one API and PostgreSQL database. This checkout contains an **incomplete implementation**, not the full product in the supplied master prompt. The API currently has tenant-scoped authentication, request management, assignment and technician status flows, estimate versions and approvals, inventory movements, and event history. The web client is still a small API-backed request screen; the Android code remains a scaffold.

## Current status

| Component | Implemented in this checkout | Not implemented yet |
|---|---|---|
| Backend | FastAPI, PostgreSQL async connection, JWT login, organization isolation, requests, assignments and technician response, estimate versions/approval, inventory movements, notes, notifications, audit records, idempotency, event history, Alembic migration, deterministic demo seed | SLA and maintenance workers, protected file upload/download, user/property/equipment/category management endpoints, feedback, live updates, full PostgreSQL concurrency tests |
| Web | Responsive Russian/English sign-in and customer request screen; API list filtering/pagination and localized request status labels | Dispatcher/admin/technician workspaces, assignment/estimate/inventory pages, profile/settings/analytics, full error localization, live updates, accessibility review, browser build and tests |
| Android | Flutter source scaffold and SQLite persistent outbox primitives | Login/API sync UI, assigned task workflow, notes/photos/materials, conflict resolution, notifications, Android project wrapper and APK |

No APK, demonstration video, or deployable production build is included. Docker Desktop is installed, but this session receives access denied from its engine pipe, so the Compose services have not been started here.

## Requirements

- Docker Compose v2
- `uv` 0.13+ and Python 3.13+ for local backend commands
- Bun 1.4+ for local web commands
- Flutter 3.24+ and Android SDK for mobile commands (not available in the environment used to prepare this checkout)

## Run API and web with Docker

From this directory:

```sh
cp .env.example .env
```

Replace both placeholder secrets in `.env`, then run:

```sh
docker compose up --build
```

The database uses a persistent named volume. Migrations run after PostgreSQL reports healthy. Open the web application at <http://localhost:3000>; API documentation is at <http://localhost:8000/api/v1/docs>. Health checks are at <http://localhost:8000/health/live> and <http://localhost:8000/health/ready>.

Seed the demo data in a separate terminal after startup:

```sh
docker compose exec backend uv run --no-sync python -m app.seed
```

Seed prints the two organization IDs and demo password `FixFlow-Demo-Only-2026!`. Accounts are `customer-1@demo.fixflow.local`, `dispatcher-1@demo.fixflow.local`, `organization_admin-1@demo.fixflow.local`, and `technician-1@demo.fixflow.local` (replace `-1` with `-2` for the second organization). This seed command is demo-only. It deliberately skips any nonempty database and is not a production account provisioning mechanism.

## Local development

Backend: set `DATABASE_URL` and a `JWT_SECRET` of at least 32 characters, then from `backend/` run `uv sync`, `uv run alembic upgrade head`, and `uv run uvicorn app.main:app --reload`.

Web: from `web/`, run `bun install`, set `NEXT_PUBLIC_API_URL` if the API is not at `http://localhost:8000/api/v1`, then run `bun run dev`.

Mobile source is under `mobile/`. Flutter commands cannot be reported as successful until Flutter and Android SDK are installed.

## Verification

`scripts/verify-all.sh` contains the requested checks; it has **not** passed as a whole in the current environment. See [VERIFICATION.md](docs/VERIFICATION.md) and [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for actual results and gaps. No pass is claimed for checks that could not be run.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Product decisions](docs/PRODUCT_DECISIONS.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
- [Verification](docs/VERIFICATION.md)
- [AI usage](docs/AI_USAGE.md)

Demonstration video: not recorded yet.
