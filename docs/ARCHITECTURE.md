# Architecture

The system is planned as a web client and Android client calling one FastAPI service backed by PostgreSQL. In this initial implementation, the API owns authentication, tenant scope, request transitions, and persistence. Web requests carry a bearer token; authenticated API queries derive organization and role from the server-verified token and user row. Customer request listings additionally filter by the caller's user ID.

## Current data model

`organizations` own `users`, `service_requests`, `request_events`, and `idempotency_records`. Request and event reads include organization predicates. A status update locks the request row before applying the transition and writing its history event in the same transaction. A composite organization/key uniqueness constraint makes request creation retries durable.

## Domain schema

The initial schema now defines memberships, technicians and skills, properties/assets/categories, assignment windows, estimate versions and lines, inventory and movements, material use, SLA clocks/events, maintenance plans/occurrences, notes, protected-attachment metadata, notifications, audit logs, and customer feedback. Assignments, estimates, stock operations, notes, notifications, and audit writes have API workflows covered by SQLite integration tests. SLA and maintenance processing, attachment transport, and feedback workflows remain unfinished. SQLite tests do not verify PostgreSQL locking or concurrent behavior.

## Data conventions

UUID primary keys; UTC timestamps; organization timezone defaults to `Asia/Bishkek`; currency and estimate line amounts are intended to use integer tыйын (100 тыйын per KGS). No money model exists in this first slice.
