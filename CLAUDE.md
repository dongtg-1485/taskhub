# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

TaskHub — a multi-tenant task management API (User → Workspace → Project → Task, plus Label, Comment, Notification). Built on the FastAPI full-stack template (copier) and being incrementally migrated from the template's generic User/Item domain to the TaskHub domain. See `docs/requirement.md`, `docs/database-design.md`, and `docs/tasks.md` (the live implementation tracker) for scope and current status.

Backend lives in `backend/`. A React/Chakra `frontend/` exists from the template but is not the focus of TaskHub work.

**Docstrings and inline comments are written in Vietnamese.** Match this when editing existing backend modules.

## Commands

All backend commands run from `backend/`:

```bash
cd backend
fastapi dev app/main.py          # run dev server (requires DB up); http://localhost:8000/docs
bash scripts/lint.sh             # mypy app + ruff check + ruff format --check (CI gate)
bash scripts/format.sh           # ruff check --fix + ruff format (autofix)
bash scripts/test.sh             # coverage run -m pytest tests/ + html report
pytest tests/path/to/test.py::test_name   # run a single test
alembic upgrade head             # apply migrations
alembic revision --autogenerate -m "msg"  # create migration (import models in app/models/__init__.py first)
```

Full stack via Docker (DB + backend + frontend + Adminer + Mailcatcher + Traefik) from repo root:

```bash
docker compose watch             # start; http://localhost:8000 (api), :8080 (adminer), :1080 (mailcatcher)
docker compose logs backend
docker compose down [-v]
```

`mypy` runs in `strict` mode and `ruff` bans `print` (T201) — both must pass clean.

## Architecture

The backend is mid-migration and runs **two parallel stacks**. Understanding which one a given route uses is the single most important thing:

### Legacy stack (template-provided, synchronous)
- Routes: `app/api/routes/{login,users,items,utils,private}.py`
- Sync `Session` from `engine` via `get_db` / `SessionDep` in `app/api/deps.py`
- Business logic in the flat `app/crud.py`
- Auth via `get_current_user` / `CurrentUser` (sync, reads from `SessionDep`)
- Schemas in `app/models/_schemas.py` (Item, Message, Token, etc.) — kept for backward compat

### New TaskHub stack (async, repository pattern)
- Routes: `app/api/routes/auth.py` (more to come per `docs/tasks.md`)
- Async `AsyncSession` from `async_engine` via `get_async_session` / `AsyncSessionDep`
- **Unit of Work**: `get_async_session` auto-commits on success, rolls back on exception. Therefore **repositories use `flush()`/`refresh()`, never `commit()`** — the session dependency owns the transaction boundary.
- Data access through repositories in `app/repositories/`, each subclassing `BaseRepository` (generic CRUD + `Page`/pagination helper in `base.py`). Repositories are instantiated as **module-level singletons in `app/repositories/__init__.py`** (`users`, `tasks`, `workspaces`, …) — import those instances, don't construct new ones. They are stateless; the `AsyncSession` is passed into every method.

Both engines are defined in `app/core/db.py` and share `SQLALCHEMY_DATABASE_URI` (PostgreSQL via psycopg). When adding TaskHub endpoints, use the async repository stack.

### Models
`app/models/` holds SQLModel tables split per entity (`user`, `workspace`, `project`, `task` [includes `Label`, `TaskLabel`], `comment`) plus `enums.py` and `auth.py`. **`app/models/__init__.py` imports models in strict FK-dependency order** (enums → user → workspace → project → task → comment) so SQLModel metadata populates correctly — keep that ordering and the `# ruff: noqa: I001` that prevents isort from reordering it. New models must be exported here for Alembic autogenerate to see them. `app/models/base.py` provides `created_at_col()` / `updated_at_col()` column factories (timezone-aware, server-side defaults).

### Auth
- Passwords: `pwdlib` with Argon2 (new) + Bcrypt (verify legacy), in `app/core/security.py`. `verify_password` returns `(is_valid, new_hash)` and callers persist `new_hash` to auto-upgrade bcrypt → argon2.
- JWT access tokens (HS256, stateless) + opaque refresh tokens stored as SHA-256 hashes in the `refresh_tokens` table for revocation. Refresh does token rotation (revoke old, issue new). See `app/api/routes/auth.py`.
- RBAC roles exist as enums (`UserRole`, `WorkspaceMemberRole`) but the per-resource RBAC dependency is not yet implemented (see `docs/tasks.md`).

### Not yet wired
Redis caching and email background tasks are required features (per `docs/requirement.md`) but **not yet present** in `compose.yml` or the code. Check `docs/tasks.md` before assuming infrastructure exists.

## Migrations

Initial schema: `app/alembic/versions/0001_initial_taskhub_schema.py`. Older template migrations are parked in `app/alembic/versions/_archive/` (not in the active chain). `app/_legacy_models.py` is retained reference, not active.
