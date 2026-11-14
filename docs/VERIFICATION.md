# Verification record

This record distinguishes files written from commands that were actually executed. No full product verification is claimed.

## Environment observed

- `uv 0.13.7`, `bun 1.4.4`, Docker Compose `5.7.0`, Node `v24.22.1`, Git `2.56.0` were available.
- Python 3.14.7 exists under the uv-managed Python directory, although the Windows Store `python.exe` shim failed to launch. Python 3.13+ is the project requirement.
- Flutter and npm executables were not found. Android SDK availability was not established.
- Docker CLI is present, but the Docker Desktop Linux engine pipe is unavailable to this session.
- The original workspace folder was not a Git repository. The project is being initialized as a local repository with one initial commit; no remote is configured.

## Checks

| Check | Result |
|---|---|
| Workspace and required tools inspection | Completed; see environment above |
| Backend Ruff check | Passed (`ruff check app tests alembic`) |
| Backend Ruff format check | Passed (`ruff format --check app tests alembic`) |
| Backend type check | Passed (`ty check app tests alembic`) |
| Backend tests | 3 passed; one Python 3.14 deprecation warning |
| Python source compilation | Passed (`compileall` on app, Alembic, and tests) |
| Web lint/type/test/build | Not run: Bun fails with `EBADF accessing temporary directory` even with a writable workspace temp path; no `bun.lock` was generated |
| Flutter analyze/test/APK | Not runnable here: Flutter executable unavailable |
| Docker Compose startup and smoke test | Not run: Docker Engine pipe unavailable |
| Compose file syntax | Passed (`docker compose config --quiet`) |
| Demo seed against PostgreSQL | Not run: PostgreSQL service unavailable |

The backend tests cover the request transition table only. No HTTP integration, PostgreSQL, authentication, authorization isolation, idempotency, concurrency, or multi-client end-to-end scenario was executed. Ruff/type/source checks do not prove the API can start in this host environment.

Do not treat a command listed in `scripts/verify-all.sh` as a passing result. Update this file with actual outputs after running the checks.
