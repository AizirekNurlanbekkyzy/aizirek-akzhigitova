# Known limitations

- This is an early vertical slice, not the full FixFlow system requested.
- No assigned-technician model exists, so technician status changes are denied.
- There are no property/equipment/category, estimate, inventory, SLA, preventive maintenance, attachments, notification, audit, or feedback workflows.
- The web UI only provides sign-in, request listing, creation, and language toggle; error strings and status labels are not fully localized, and role-specific navigation is absent.
- There is no token refresh/logout endpoint, account management, invitation flow, rate limiting, password reset, brute-force protection, or hardened production secret policy.
- File upload, object storage, malware scanning, and protected download authorization are absent.
- Live updates (WebSocket/SSE), search filters beyond title, request detail view, scheduling, and analytics are absent.
- Mobile is only a Flutter shell plus durable local command table; synchronization transport, login, tasks, photos, conflict UI, and generated Android wrapper/APK are absent.
- Demo seed has two organizations, four roles per organization, and fifty requests, but not the requested full fixture coverage. It exits when any organization is present.
- The initial Alembic migration creates current metadata on a fresh database. It is not a safe schema evolution strategy.
- Seed demo credentials are public and must never be used outside a local demo environment.
- No video link has been supplied or created.
