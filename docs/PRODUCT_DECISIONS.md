# Product decisions

## Repeat-safe request submission

**Problem:** unstable mobile or browser connections can tempt a user to tap “Create” more than once and create duplicate maintenance jobs.

**Behavior:** request creation requires a client-generated `Idempotency-Key`. The API stores the normalized request payload hash and resulting request ID in the same database transaction. A retry with the same key and content returns the first request; reuse with different content returns a conflict. This is implemented for request creation only.

**How to verify:** submit a request with one key twice and confirm the same ID; then reuse the key with a changed title and confirm HTTP 409.

## Material trade-offs in this slice

1. **Organization selection at login:** the API asks for an organization UUID, which avoids ambiguous tenant selection in this prototype but is poor onboarding UX. A secure membership discovery/selection flow is still needed.
2. **JWT bearer token in browser storage:** this keeps the initial web client simple, but persistent browser storage has greater exposure to script injection than an HttpOnly cookie design. Production deployment needs a reviewed session strategy and CSRF/CSP controls.
3. **Deny technician mutations until assignments exist:** this leaves the intended technician flow unavailable, but prevents unassigned cross-request status changes while the assignment domain is absent.
4. **Initial schema migration uses SQLAlchemy metadata creation:** suitable only for a fresh prototype database; future schema evolution needs explicit, reviewed Alembic operations and tested upgrades.
