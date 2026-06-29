# TaskHub — Task Tracking

> Mapping **Function → API → Tech Stack** kèm trạng thái thực hiện.
> Đối chiếu source code tại branch `design-db-and-create-models` (cập nhật: 2026-06-26).

## Chú thích trạng thái

| Ký hiệu | Ý nghĩa |
|:-:|---------|
| ✅ | **Done** — đã implement & có trong code |
| 🟡 | **In Progress** — làm dở (thường: model/repository đã có, nhưng API route / wiring chưa xong) |
| ⬜ | **Todo** — chưa bắt đầu |

**Tình trạng nền tảng (đã có sẵn):**
- ✅ Models đầy đủ: `app/models/` (user, workspace, project, task, label, comment, enums, refresh_token)
- ✅ Repositories async đầy đủ: `app/repositories/` (base + 6 entity + refresh_token)
- ✅ Alembic migration `0001_initial_taskhub_schema.py`
- ✅ Async DB session (`app/core/db.py`)
- ✅ Redis service trong `compose.yml` + `app/core/redis.py` + `RedisDep` trong `app/api/deps.py`
- ✅ Routes: `workspaces.py`, `projects.py`, `tasks.py` đã được đăng ký trong `app/api/main.py`

---

## 1. Auth

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| AUTH-1 | Register | `POST /api/v1/auth/register` | bcrypt/argon2 hashing, validation | ✅ | `app/api/routes/auth.py` — async repo pattern, 201 Created, 409 nếu email trùng |
| AUTH-2 | Login (cấp access token) | `POST /api/v1/auth/login` | JWT access, verify password | ✅ | `auth.py::login` (async); `POST /login/access-token` cũ vẫn còn cho Swagger legacy |
| AUTH-3 | Login (cấp refresh token) | `POST /api/v1/auth/login` | opaque refresh token, DB store (SHA-256 hash) | ✅ | `auth.py::login` trả `TokenPair` (access + refresh); lưu hash qua `refresh_tokens.create_token` |
| AUTH-4 | Refresh token | `POST /api/v1/auth/refresh` | verify refresh → cấp cặp mới, **token rotation** | ✅ | `auth.py::refresh`; check revoked/expired/inactive, revoke token cũ rồi cấp mới |
| AUTH-5 | Logout (revoke refresh) | `POST /api/v1/auth/logout` | DB revoke (soft-delete), idempotent | ✅ | `auth.py::logout`; revoke qua `refresh_tokens.revoke` |

## 2. User

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| USER-1 | Get profile | `GET /api/v1/users/me` | `get_current_user`, JWT | ✅ | `read_user_me` (`users.py`) |
| USER-2 | Update profile | `PATCH /api/v1/users/me` | validation, auth | ✅ | `update_user_me` |
| USER-3 | Change password | `PATCH /api/v1/users/me/password` | bcrypt/argon2, auth | ✅ | `update_password_me` — verify current password rồi hash mới, lưu argon2 |

## 3. Workspace

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| WS-1 | CRUD workspace (owner only) | `POST` / `GET /api/v1/workspaces/{id}` | RBAC (OWNER), resource ownership | ✅ | POST (201) + GET /me + GET / (superuser) + GET /{id} + PATCH /{id} + DELETE /{id} — đầy đủ CRUD |
| WS-2 | Invite member | `POST /api/v1/workspaces/{id}/members` | RBAC, Background Task (email) | ✅ | Route `invite_users` với OWNER dep; BackgroundTasks gửi email khi `emails_enabled` |
| WS-3 | Remove member | `DELETE /api/v1/workspaces/{id}/members/{user_id}` | RBAC, ownership check | ✅ | `remove_member` (`workspaces.py`) — dùng `WorkspaceOwnerDep` |
| WS-4 | Phân quyền theo role | (áp dụng mọi WS endpoint) | RBAC (OWNER/EDITOR/VIEWER) | ✅ | `require_workspace_role(min_role)` factory trong `deps.py`; alias `WorkspaceOwnerDep`, `WorkspaceEditorDep`, `WorkspaceViewerDep` áp vào mọi route workspace |

## 4. Project

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| PRJ-1 | CRUD project trong workspace | `POST /api/v1/workspaces/{id}/projects` | RBAC (EDITOR+) | ✅ | POST (create, EDITOR+) + GET /{id} + PATCH /{id} (EDITOR+) + DELETE /{id} (OWNER) trong `projects.py` — đầy đủ CRUD |
| PRJ-2 | Archive project | `PATCH /api/v1/projects/{id}/archive` | RBAC, cache invalidate | ✅ | `archive_project` + `unarchive_project` trong `projects.py` — EDITOR+ check; 400 nếu đã ở trạng thái đó |

## 5. Task

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| TASK-1 | List tasks (filter + pagination) | `GET /api/v1/projects/{id}/tasks` | Redis cache, filter/paginate, RBAC | ✅ | `list_tasks` (`projects.py`) — filter theo status/priority/assignee_id, cache-aside Redis, membership check |
| TASK-2 | Create task | `POST /api/v1/projects/{id}/tasks` | RBAC, cache invalidate | ✅ | `create_task` (`projects.py`) — membership check, cache invalidation |
| TASK-3 | Update task (status/priority/due_date) | `PATCH /api/v1/tasks/{id}` | RBAC, cache invalidate | ✅ | `update_task` (`tasks.py`) — membership check, cache invalidation qua `invalidate_by_pattern` |
| TASK-4 | Assign task cho member | `PATCH /api/v1/tasks/{id}` | RBAC, Background Task (email notify) | ⬜ | `assignee_id` có trong `UpdateTaskRequest`; **email assign + RBAC check chưa có** |
| TASK-5 | Delete task | `DELETE /api/v1/tasks/{id}` | RBAC, cache invalidate | ✅ | `delete_task` (`tasks.py`) — membership check, cache invalidation |

## 6. Label

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| LBL-1 | CRUD label (per project) | `POST /api/v1/projects/{id}/labels` (+CRUD) | RBAC (EDITOR+) | 🟡 | `Label` model + `LabelRepository` đã có; **route chưa tạo** |
| LBL-2 | Gán / bỏ label cho task | `POST /api/v1/tasks/{id}/labels/{label_id}` | RBAC, cache invalidate | 🟡 | `TaskLabel` M:N join có; route chưa |

## 7. Comment

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| CMT-1 | Thêm comment trên task | `POST /api/v1/tasks/{id}/comments` | auth, `get_current_user` | 🟡 | `Comment` model + repo đã có; **route chưa tạo** |
| CMT-2 | Xóa comment | `DELETE /api/v1/tasks/{id}/comments/{comment_id}` | RBAC / ownership | 🟡 | Repo `delete` đã có; **route chưa tạo** |

## 8–14. Cross-cutting / Infra

| ID | Task | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----------|:--:|--------|
| FILT-1 | Filtering & Pagination (status/priority/assignee + page/limit) | query params + `Page[T]` | ✅ | Áp dụng trong `list_tasks` — query params status/priority/assignee_id + page/limit |
| CACHE-1 | Redis cache cho `GET /projects/{id}/tasks` | redis-py, cache aside | ✅ | `RedisDep` trong `deps.py`, Redis pool trong `core/redis.py`, service redis trong `compose.yml`; cache-aside pattern trong `list_tasks` |
| CACHE-2 | Cache invalidation khi task thay đổi | redis | ✅ | `invalidate_by_pattern` được gọi trong create/update/delete task |
| BG-1 | Background task gửi email khi assign | `emails` lib, BackgroundTasks/queue | ⬜ | `emails` đã có trong deps; chưa wiring trigger assign |
| RBAC-1 | RBAC ADMIN/OWNER/EDITOR/VIEWER theo từng resource | dependency injection | ⬜ | Enum có; chỉ có owner-check thủ công, dependency RBAC chưa viết |
| DOC-1 | Swagger/ReDoc + Bearer scheme + document error responses | FastAPI OpenAPI | 🟡 | Auto docs + OAuth2 Bearer ✅; document error responses chi tiết chưa |
| DOCK-1 | Docker compose full stack (app + DB + Redis) | Dockerfile, compose | ✅ | Có `db`, `backend`, `frontend`, `adminer`, `prestart`, `redis:7-alpine` trong `compose.yml` |
| QA-1 | Ruff lint pass 100% + mypy no error | ruff, mypy | 🟡 | Config có trong `pyproject.toml`; cần chạy verify trên code mới |
| LOG-1 | Logging | logging/structlog | ⬜ | Chưa thấy cấu hình logging tập trung |
| MW-1 | Middleware & exception handling (global) | FastAPI middleware/handlers | ⬜ | Chưa thấy custom exception handler tập trung |

---

## Tổng kết tiến độ

| Nhóm | ✅ Done | 🟡 In Progress | ⬜ Todo |
|------|:--:|:--:|:--:|
| Auth | 5 | 0 | 0 |
| User | 3 | 0 | 0 |
| Workspace | 4 | 0 | 0 |
| Project | 2 | 0 | 0 |
| Task | 4 | 0 | 1 |
| Label | 0 | 2 | 0 |
| Comment | 0 | 2 | 0 |
| Infra/Cross-cutting | 4 | 2 | 4 |
| **Tổng** | **22** | **6** | **5** |

### Gợi ý thứ tự ưu tiên (next steps)
1. **LBL-1, LBL-2** — tạo route label (`POST/GET/PATCH/DELETE /projects/{id}/labels`, gán/bỏ label cho task).
2. **CMT-1, CMT-2** — tạo route comment (`POST/DELETE /tasks/{id}/comments`).
3. **TASK-4** — wiring background email khi assign task (phụ thuộc BG-1).
4. **BG-1** — background email notification (dùng `emails` lib, `BackgroundTasks`).
5. **LOG-1, MW-1, DOC-1, QA-1** — hoàn thiện chất lượng & vận hành.
