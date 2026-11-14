# Known limitations

- This is an early vertical slice, not the full FixFlow system requested.
- The API has tested workflows for requests, assignments, technician status changes, estimates, inventory, notes, and notifications. Audit records are written for key operations. SLA processing, preventive maintenance, protected file transfer, and feedback workflows are absent.
- The web UI only provides sign-in, request listing, creation, and language toggle; error strings and status labels are not fully localized, and role-specific navigation is absent.
- There is no token refresh/logout endpoint, account management, invitation flow, rate limiting, password reset, brute-force protection, or hardened production secret policy.
- File upload, object storage, malware scanning, and protected download authorization are absent.
- Live updates (WebSocket/SSE), search filters beyond title, analytics, and a complete administrative UI are absent.
- Mobile is only a Flutter shell plus durable local command table; synchronization transport, login, tasks, photos, conflict UI, and generated Android wrapper/APK are absent.
- Demo seed has two organizations, four roles per organization, and fifty requests, but not the requested full fixture coverage. It exits when any organization is present.
- The initial Alembic migration is a frozen PostgreSQL DDL snapshot. Future schema changes require additional migrations.
- Docker Desktop is installed, but Docker CLI calls in this session cannot access the engine named pipe, and Docker Desktop's own CLI cannot read its per-user install registry key. PostgreSQL/container startup and native PostgreSQL lock behavior remain unverified.
- Seed demo credentials are public and must never be used outside a local demo environment.
- No video link has been supplied or created.
