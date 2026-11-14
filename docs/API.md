# API

All implemented routes use `/api/v1`. Interactive OpenAPI documentation is served at `/api/v1/docs` when the API is running.

## Authentication

`POST /api/v1/auth/login`

```json
{"email":"customer-1@demo.fixflow.local","password":"FixFlow-Demo-Only-2026!","organization_id":"<UUID printed by seed>"}
```

Returns a bearer token. Protected routes require `Authorization: Bearer <token>`. The organization ID is selected at login and is embedded in the signed token; the API resolves the active user again on each request.

## Requests

- `POST /api/v1/requests` — create request; requires `Idempotency-Key` header, title 5–120 chars, description 20–3000 chars, and priority `LOW`, `NORMAL`, or `HIGH`.
- `GET /api/v1/requests?page=1&page_size=20&search=...` — paginated organization requests; customers only see their own.
- `GET /api/v1/requests/{id}` — request summary; customers only see their own.
- `PATCH /api/v1/requests/{id}/status` — apply an allowed transition, optionally with a reason.
- `GET /api/v1/requests/{id}/history` — request status event history.
- `POST /api/v1/requests/{id}/assignments` — dispatcher/admin schedules an active technician; checks required category skills, local working hours, and overlapping assignments.
- `GET /api/v1/technicians/me`, `GET /api/v1/technician/assignments` — technician profile and active assigned work.
- `POST /api/v1/assignments/{id}/accept` or `/decline` — technician response.
- `POST /api/v1/requests/{id}/estimates` — dispatcher/admin creates an idempotent estimate draft with line items.
- `PUT /api/v1/estimates/{id}` — edit a draft; submitted versions return 409.
- `POST /api/v1/estimates/{id}/submit`, `/decision`, and `/revise` — submit for approval, customer approve/reject, or create a linked revision.
- `GET /api/v1/requests/{id}/estimates`, `GET /api/v1/estimates/{id}/events` — version list and estimate history.
- `POST /api/v1/inventory/items` — admin creates an item.
- `GET /api/v1/inventory/items` — dispatcher/admin lists tenant inventory.
- `POST /api/v1/inventory/items/{id}/movements` — dispatcher/admin records a keyed stock receipt/issue; locked quantity updates reject negative stock.
- `GET/POST /api/v1/requests/{id}/notes` — read/write notes with tenant, customer, and assignment access checks; customers cannot see internal notes. Writes are idempotent.
- `GET /api/v1/notifications`, `POST /api/v1/notifications/{id}/read` — list the signed-in user notifications and mark one read.
- `GET /health/live`, `GET /health/ready` — process liveness and database readiness checks.

Errors use FastAPI's JSON `detail` response. Authentication failures return 401, role failures 403, missing or out-of-scope IDs 404, invalid transitions and idempotency payload reuse 409, and schema validation 422. An organization-scoped request key can be reused with the same payload to return the original request; a changed payload returns 409. The unique organization/key constraint and conflict recovery cover concurrent identical submissions.

Admin CRUD, SLA/maintenance processing, file transfer, feedback, and live event endpoints remain unimplemented.
