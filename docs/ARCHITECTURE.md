# Architecture

The system is planned as a web client and Android client calling one FastAPI service backed by PostgreSQL. In this initial implementation, the API owns authentication, tenant scope, request transitions, and persistence. Web requests carry a bearer token; authenticated API queries derive organization and role from the server-verified token and user row. Customer request listings additionally filter by the caller's user ID.

## Current data model

`organizations` own `users`, `service_requests`, `request_events`, and `idempotency_records`. Request and event reads include organization predicates. A status update locks the request row before applying the transition and writing its history event in the same transaction. A composite organization/key uniqueness constraint makes request creation retries durable.

## Planned domain expansion

Technicians/skills, properties/assets, assignments, estimates and immutable estimate versions, inventory and movements, SLA events, maintenance occurrences, notes/attachments, notifications, and audit records remain to be modeled. Schedule and inventory concurrency require PostgreSQL transactions with exclusion/row locks and conditional stock updates respectively. These controls are not present yet.

## Data conventions

UUID primary keys; UTC timestamps; organization timezone defaults to `Asia/Bishkek`; currency and estimate line amounts are intended to use integer tыйын (100 тыйын per KGS). No money model exists in this first slice.
