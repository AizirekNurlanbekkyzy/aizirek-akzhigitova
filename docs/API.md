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

Errors use FastAPI's JSON `detail` response. Authentication failures return 401, role failures 403, missing or out-of-scope IDs 404, invalid transitions and idempotency payload reuse 409, and schema validation 422. An organization-scoped request key can be reused with the same payload to return the original request; a changed payload returns 409. The unique organization/key constraint and conflict recovery cover concurrent identical submissions.

The broader endpoint set in the master prompt has not been implemented.
