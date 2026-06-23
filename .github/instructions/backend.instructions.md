---
description: "Use when writing, editing, or reviewing backend Python code: FastAPI routes, repositories, models, schemas, migrations, tests, or auth logic. Covers async stack, repository pattern, Unit of Work, schema conventions, and code style for the TaskHub backend."
applyTo: "backend/**"
---

# TaskHub Backend — Coding Conventions

## Language

- **Docstrings và inline comments viết bằng tiếng Việt.** Match this when editing any existing module.
- English is used only for: HTTP response descriptions in route docstrings, FastAPI `responses={}` dict descriptions, and git commit messages.

## Dual Stack — Know Which One to Use

The backend has two parallel stacks. **Always use the async (TaskHub) stack for new endpoints.**

| | Legacy stack | TaskHub stack (new) |
|---|---|---|
| Session | Sync `Session` via `SessionDep` | Async `AsyncSession` via `AsyncSessionDep` |
| Session source | `get_db` → `engine` | `get_async_session` → `async_engine` |
| Business logic | `app/crud.py` | `app/repositories/` |
| Auth dependency | `CurrentUser` (sync) | `CurrentUser` (async) |
| Routes | `login`, `users`, `items`, `utils`, `private` | `auth`, `workspaces` (and new TaskHub routes) |

**Never mix sync `Session` with async repository calls or vice versa.**

## Unit of Work — Transaction Boundary

`get_async_session` owns the transaction: it auto-commits on success and rolls back on exception.

- Repositories **must use `flush()` + `refresh()`**, never `commit()`.
- Never call `session.commit()` inside a repository or route handler.
- `flush()` writes SQL to DB within the current transaction; `refresh()` loads server-generated values (id, created_at, sequences).

```python
# ✅ Correct — in a repository method
session.add(db_obj)
await session.flush()
await session.refresh(db_obj)
return db_obj

# ❌ Wrong — never commit inside a repo or route
await session.commit()
```

## Repository Pattern

- All data access goes through repositories in `app/repositories/`.
- Each repository subclasses `BaseRepository[ModelT]` and declares `model: ClassVar[type[Any]]`.
- Repositories are **module-level singletons** in `app/repositories/__init__.py`. Import those instances — do not instantiate new ones in routes or elsewhere.
- Custom query methods override or extend base methods; use keyword-only args (`*`) for clarity.
- Raise no HTTP exceptions inside repositories — return `None` or raise domain-level errors only.

```python
# ✅ Correct — import singleton
from app.repositories import workspaces, workspace_members

# ❌ Wrong — never instantiate in a route
repo = WorkspaceRepository()
```

## Models (`app/models/`)

- SQLModel table classes go in per-entity files: `user.py`, `workspace.py`, `project.py`, `task.py`, `comment.py`.
- Always use `created_at_col()` / `updated_at_col()` from `app.models.base` for timestamp columns (timezone-aware, server-side defaults).
- UUID primary keys: `id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)`.
- Foreign key fields include `ondelete="CASCADE"` where applicable.
- **Export new models from `app/models/__init__.py` in strict FK-dependency order** (enums → user → workspace → project → task → comment) so Alembic autogenerate works correctly. Keep the `# ruff: noqa: I001` comment — never let isort reorder these imports.

## Schemas (`app/schemas/`)

- Pydantic/SQLModel schemas (request/response) live in `app/schemas/`, one file per domain entity.
- Naming conventions:
  - `{Entity}Response` — response schema for a single entity
  - `{Entity}sResponse` — paginated list response with `data: list[...]` and `count: int`
  - `Create{Entity}Request` — creation payload
  - `Update{Entity}Request` — update payload (fields optional)
  - `{Action}{Entity}Request` — action-specific request (e.g., `InviteMemberRequest`)
- Export schemas from both `app/schemas/__init__.py` and `app/models/__init__.py` (for backward compat and single-import convenience).
- Use `SQLModel` as base class for schemas (not plain `BaseModel`).

## FastAPI Routes

- Route files go in `app/api/routes/`, one file per domain (e.g., `workspaces.py`).
- Register routers in `app/api/main.py`.
- Route signature pattern — use keyword-only separator `*` to prevent positional argument confusion:
  ```python
  @router.post("/", response_model=WorkspaceResponse)
  async def create_workspace(
      *,
      session: AsyncSessionDep,
      current_user: CurrentUser,
      body: CreateWorkspaceRequest,
  ) -> WorkspaceResponse:
  ```
- Always specify `response_model` on route decorators.
- Use `status.HTTP_201_CREATED` for POST endpoints that create resources.
- Declare `responses={409: {"description": "..."}}` for well-known error codes.
- Raise `HTTPException` directly in route handlers — not inside repositories.
- Return `model_validate(orm_obj)` to convert ORM objects to response schemas:
  ```python
  return WorkspaceResponse.model_validate(workspace)
  ```

## Authentication & Authorization

- Inject the authenticated user with `CurrentUser` (from `app.api.deps`), which is `Annotated[User, Depends(get_current_user)]`.
- Protect superuser-only routes with `dependencies=[Depends(get_current_active_superuser)]`.
- Per-resource RBAC helpers (e.g., `_is_workspace_owner`) are defined as private async functions in the route module.
- JWT access tokens are stateless (HS256). Refresh tokens are opaque, stored as SHA-256 hashes in the `refresh_tokens` table.
- `verify_password` returns `(is_valid, new_hash)` — if `new_hash` is not `None`, persist it to auto-upgrade bcrypt → argon2.

## Alembic Migrations

- Run `alembic revision --autogenerate -m "msg"` from `backend/` after adding/changing models.
- Import new models in `app/models/__init__.py` **before** generating a revision, or they won't be detected.
- The active migration chain starts from `0001_initial_taskhub_schema.py`. Older template migrations are in `_archive/` and not in the active chain.

## Linting & Type Checking

- `mypy` runs in **strict** mode — all functions must have full type annotations.
- `ruff` bans `print` (T201) — use logging instead.
- Run before committing:
  ```bash
  bash scripts/lint.sh   # mypy + ruff check + ruff format --check
  bash scripts/format.sh # ruff check --fix + ruff format (autofix)
  ```
- `app/models/__init__.py` carries `# ruff: noqa: I001` — do not remove it.

## Tests

- Tests live in `backend/tests/`. Run: `bash scripts/test.sh` (coverage + HTML report).
- Existing tests use the **legacy sync stack** with `TestClient` and sync `Session` fixtures.
- New TaskHub route tests should use async test patterns with `AsyncClient` and `AsyncSession` (see `anyio` / `httpx` async client pattern).
- Run a single test: `pytest tests/path/to/test.py::test_name`.
