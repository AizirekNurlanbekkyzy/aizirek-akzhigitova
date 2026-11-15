# Known limitations

- This is an early vertical slice, not the full FixFlow system requested.
- The API has tested workflows for requests, assignments, technician status changes, estimates, inventory, notes, and notifications. Audit records are written for key operations. SLA processing, preventive maintenance, protected file transfer, and feedback workflows are absent.
- The web UI provides role-aware sections for the four roles, customer registration, requests, estimates, technician list, scheduling, technician tasks, and inventory. Estimate editing/revision screens, property/equipment selection, notification center, analytics, and live updates remain incomplete.
- Web tokens are held in browser local storage; a hardened production session should move to secure HttpOnly cookies. There is no token refresh endpoint, invitation flow, rate limiting, password reset, or brute-force protection.
- File upload, object storage, malware scanning, and protected download authorization are absent.
- Live updates (WebSocket/SSE), search filters beyond title, analytics, and a complete administrative UI are absent.
- Mobile has a Flutter technician workflow with secure login, assignments, request details, status actions, and notes. Flutter/Android SDK are unavailable here, so the Android wrapper, APK, and device run are not verified. Background offline synchronization, photos/materials, and push notifications remain incomplete.
- Demo seed adds two organizations, four roles per organization, fifty requests, technicians/working hours/skills, property/equipment, draft estimates, and stock. It uses stable IDs, is additive, and refuses production mode.
- The initial Alembic migration is a frozen PostgreSQL DDL snapshot. Future schema changes require additional migrations.
- Docker Desktop is installed, but Docker CLI calls in this session receive access denied from the engine named pipe. Compose configuration validation passes; PostgreSQL/container startup, migrations, restart persistence, and native PostgreSQL locking remain unverified.
- Seed demo credentials are public and must never be used outside a local demo environment.
- No video link has been supplied or created.
