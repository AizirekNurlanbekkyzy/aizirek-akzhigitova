# FixFlow — Aizirek Akzhigitova

FixFlow connects customer service, dispatch, estimates, field work, and inventory through one API and PostgreSQL database. It is a development/demo foundation, not yet the complete production product. The Next.js web client uses the real API and adapts its sections to customer, dispatcher, administrator, and technician roles.

## Current status

| Component | Implemented in this checkout | Not implemented yet |
|---|---|---|
| Backend | FastAPI, email/password login and customer registration, organization isolation, requests, assignments, estimate versions/approval, inventory movements, notes, notifications, admin audit feed, idempotency, event history, Alembic, additive demo seed | SLA and maintenance workers, protected file upload/download, user/property/equipment/category CRUD, feedback, live updates, full PostgreSQL concurrency tests |
| Web | Responsive Russian/English application; role-aware dashboard, requests, estimates, technician list, schedule, technician tasks, inventory, customer registration/sign-in using only email and password; connected to the API | Estimate editing/revision UI, property/equipment selection, notification center, advanced filters/analytics, live updates, production cookie sessions and accessibility review |
| Android | Flutter technician app source: secure sign-in, assigned jobs, request details, status actions, and shared notes | Android project wrapper/APK generation, background offline synchronization, photos/materials, conflict resolution, push notifications |

No APK or deployable production build is included. [Watch the FixFlow demonstration video on YouTube](https://youtu.be/hFNOJmtK2nk). Docker Desktop is installed, but this session receives access denied from its engine pipe, so the Compose services have not been started here.

## Requirements

- Docker Compose v2
- `uv` 0.13+ and Python 3.13+ for local backend commands
- Node.js 22+ and pnpm 11.25+ for the Web client; Bun is used only by the optional Web unit test script
- Flutter 3.24+ and Android SDK for mobile commands (not available in the environment used to prepare this checkout)

## Configure local secrets

Do not copy demo credentials into a deployed environment. From this directory, create a fresh ignored `.env` file with random PostgreSQL and JWT secrets:

```powershell
.\scripts\setup-env.ps1
```

The script refuses to overwrite an existing `.env`. The file is ignored by Git; `.env.example` contains empty secret and environment fields and cannot start Compose unchanged. Set `DEFAULT_ORGANIZATION_ID` to the organization that should receive new public customer registrations; this is server-side configuration, so customers only enter their email and password. The included local `.env` targets the North demo organization. In production, use the real organization's ID, set `APP_ENV=production`, supply production-managed secrets, and do not run the demo seed command. Production startup rejects the demo organization as the public registration target. Compose requires an explicit environment value; the API rejects placeholder JWT secrets and the seed refuses production mode.

## Run API and web with Docker

From this directory, after Docker Desktop is running and `.env` has been created:

```sh
docker compose up --build
```

The database uses a persistent named volume. Migrations run after PostgreSQL reports healthy. Open the web application at <http://localhost:3000>; API documentation is at <http://localhost:8001/api/v1/docs>. Health checks are at <http://localhost:8001/health/live> and <http://localhost:8001/health/ready>.

### Open the site from a phone on the same Wi-Fi

Set `HOST_BIND=0.0.0.0` and add the laptop address to `CORS_ORIGINS` (for example, `http://192.168.1.20:3000`) for the Android app's direct API requests. The Web app calls the API through a same-origin Next.js proxy, so it does not need a separate API URL or browser CORS access. Rebuild the services after changing these values. Share `http://192.168.1.20:3000` with devices on the same trusted Wi-Fi. The database port remains bound to `127.0.0.1` and is not published to the LAN. Windows Firewall may ask to allow the app on private networks. This LAN address is temporary and may change when the router assigns a new address; this does not create an internet-hosted public site.

Seed the demo data in a separate terminal after startup:

```sh
docker compose exec backend uv run --no-sync python -m app.seed
```

Seed prints the two organization IDs and demo password `FixFlow-Demo-Only-2026!`. It adds two organizations, four demo roles per organization, 50 requests, technicians with working hours and skills, property/equipment, draft estimates, and inventory. Accounts are `customer-1@demo.fixflow.local`, `dispatcher-1@demo.fixflow.local`, `organization_admin-1@demo.fixflow.local`, and `technician-1@demo.fixflow.local` (replace `-1` with `-2` for the second organization). Stable IDs make reruns additive; the seed never deletes or resets existing data and is blocked when `APP_ENV=production`.

## Local development

Backend: set `DATABASE_URL`, a `JWT_SECRET` of at least 32 random bytes, and `APP_ENV=development` in the shell, then from `backend/` run `uv sync`, `uv run alembic upgrade head`, and `uv run uvicorn app.main:app --reload`.

Web: from `web/`, run `pnpm install --frozen-lockfile`, then run `pnpm dev`. By default the Next.js proxy forwards `/api/v1/*` to `http://localhost:8001`; set `FIXFLOW_API_ORIGIN` only when the backend listens elsewhere. Browser requests stay on the Web origin.

Mobile source is under `mobile/`; Android run and APK instructions are in `mobile/README.md`. A prebuilt APK is not included; build it on a machine with Flutter and the Android SDK installed.

## Verification

`scripts/verify-all.sh` contains the requested checks; it has **not** passed as a whole in the current environment. See [VERIFICATION.md](docs/VERIFICATION.md) and [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for actual results and gaps. No pass is claimed for checks that could not be run.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Product decisions](docs/PRODUCT_DECISIONS.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
- [Verification](docs/VERIFICATION.md)
- [AI usage](docs/AI_USAGE.md)

Demonstration video: [FixFlow on YouTube](https://youtu.be/hFNOJmtK2nk).
