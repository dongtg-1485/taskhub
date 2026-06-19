# TaskHub — Task Tracking

> Mapping **Function → API → Tech Stack** kèm trạng thái thực hiện.
> Đối chiếu source code tại branch `design-db-and-create-models` (cập nhật: 2026-06-19).

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

---

## 1. Auth

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| AUTH-1 | Register | `POST /api/v1/auth/register` | bcrypt/argon2 hashing, validation | 🟡 | Có `POST /users/signup` (`register_user`) nhưng chưa gom về namespace `/auth`; logic hash đã xong (`core/security.py`) |
| AUTH-2 | Login (cấp access token) | `POST /api/v1/auth/login` | JWT access, verify password | ✅ | `POST /login/access-token` (`login.py`); `create_access_token` đã có |
| AUTH-3 | Login (cấp refresh token) | `POST /api/v1/auth/login` | JWT refresh, Redis/DB store | 🟡 | `RefreshToken` model + `RefreshTokenRepository.create_token` đã có nhưng login chưa phát hành refresh token |
| AUTH-4 | Refresh token | `POST /api/v1/auth/refresh` | JWT verify refresh → cấp access mới | 🟡 | Repo `get_by_hash`/`revoke` đã có; **route chưa tạo** |
| AUTH-5 | Logout (revoke refresh) | `POST /api/v1/auth/logout` | Redis/DB revoke, `get_current_user` | 🟡 | Repo `revoke` / `revoke_all_for_user` đã có; **route chưa tạo** |

## 2. User

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| USER-1 | Get profile | `GET /api/v1/users/me` | `get_current_user`, JWT | ✅ | `read_user_me` (`users.py`) |
| USER-2 | Update profile | `PATCH /api/v1/users/me` | validation, auth | ✅ | `update_user_me` |
| USER-3 | Change password | `PATCH /api/v1/users/me/password` | bcrypt/argon2, auth | ✅ | `update_password_me` |

## 3. Workspace

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| WS-1 | CRUD workspace (owner only) | `POST` / `GET /api/v1/workspaces/{id}` | RBAC (OWNER), resource ownership | 🟡 | Model + `WorkspaceRepository` đã có; **route chưa tạo** |
| WS-2 | Invite member | `POST /api/v1/workspaces/{id}/members` | RBAC, Background Task (email) | 🟡 | `workspace_members` repo đã có; route + email chưa |
| WS-3 | Remove member | `DELETE /api/v1/workspaces/{id}/members/{user_id}` | RBAC, ownership check | 🟡 | Repo đã có; **route chưa tạo** |
| WS-4 | Phân quyền theo role | (áp dụng mọi WS endpoint) | RBAC (OWNER/ADMIN/EDITOR/VIEWER) | ⬜ | `WorkspaceMemberRole` enum có; dependency RBAC chưa viết |

## 4. Project

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| PRJ-1 | CRUD project trong workspace | `POST /api/v1/workspaces/{id}/projects` | RBAC (EDITOR+) | 🟡 | Model + `ProjectRepository` đã có; **route chưa tạo** |
| PRJ-2 | Archive project | `PATCH /api/v1/projects/{id}` | RBAC, cache invalidate | ⬜ | `ProjectStatus` enum có; route chưa |

## 5. Task

| ID | Task | API | Tech Stack | Trạng thái | Ghi chú |
|:--:|------|-----|-----------|:--:|--------|
| TASK-1 | List tasks (filter + pagination) | `GET /api/v1/projects/{id}/tasks` | Redis cache, filter/paginate, RBAC | 🟡 | `Page[T]` + `list()` repo đã có; route + cache + filter chưa |
| TASK-2 | Create task | `POST /api/v1/projects/{id}/tasks` | RBAC, cache invalidate | 🟡 | Repo đã có; **route chưa tạo** |
| TASK-3 | Update task (status/priority/due_date) | `PATCH /api/v1/tasks/{id}` | RBAC, cache invalidate | 🟡 | `TaskStatus`/`TaskPriority` enum có; route chưa |
| TASK-4 | Assign task cho member | `PATCH /api/v1/tasks/{id}` | RBAC, Background Task (email notify) | ⬜ | `assignee_id` FK có; route + email assign chưa |
| TASK-5 | Delete task | `DELETE /api/v1/tasks/{id}` | RBAC, cache invalidate | 🟡 | Repo `delete` đã có; **route chưa tạo** |

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
| FILT-1 | Filtering & Pagination (status/priority/assignee + page/limit) | query params + `Page[T]` | 🟡 | Hạ tầng `Page` xong; chưa áp vào route task |
| CACHE-1 | Redis cache cho `GET /projects/{id}/tasks` | redis-py, cache aside | ⬜ | **Chưa có dependency redis**, chưa có service trong compose |
| CACHE-2 | Cache invalidation khi task thay đổi | redis | ⬜ | Phụ thuộc CACHE-1 |
| BG-1 | Background task gửi email khi assign | `emails` lib, BackgroundTasks/queue | ⬜ | `emails` đã có trong deps; chưa wiring trigger assign |
| RBAC-1 | RBAC ADMIN/OWNER/EDITOR/VIEWER theo từng resource | dependency injection | ⬜ | Enum có; chỉ mới có check `superuser` trong `deps.py` |
| DOC-1 | Swagger/ReDoc + Bearer scheme + document error responses | FastAPI OpenAPI | 🟡 | Auto docs + OAuth2 Bearer ✅; document error responses chi tiết chưa |
| DOCK-1 | Docker compose full stack (app + DB + Redis) | Dockerfile, compose | 🟡 | Có `db`, `backend`, `frontend`, `adminer`, `prestart`; **thiếu service `redis`** |
| QA-1 | Ruff lint pass 100% + mypy no error | ruff, mypy | 🟡 | Config có trong `pyproject.toml`; cần chạy verify trên code mới |
| LOG-1 | Logging | logging/structlog | ⬜ | Chưa thấy cấu hình logging tập trung |
| MW-1 | Middleware & exception handling (global) | FastAPI middleware/handlers | ⬜ | Chưa thấy custom exception handler tập trung |

---

## Tổng kết tiến độ

| Nhóm | ✅ Done | 🟡 In Progress | ⬜ Todo |
|------|:--:|:--:|:--:|
| Auth | 1 | 4 | 0 |
| User | 3 | 0 | 0 |
| Workspace | 0 | 3 | 1 |
| Project | 0 | 1 | 1 |
| Task | 0 | 4 | 1 |
| Label | 0 | 2 | 0 |
| Comment | 0 | 2 | 0 |
| Infra/Cross-cutting | 0 | 4 | 6 |
| **Tổng** | **4** | **20** | **10** |

### Gợi ý thứ tự ưu tiên (next steps)
1. **AUTH-4, AUTH-5, AUTH-3** — hoàn thiện refresh/logout (repo đã sẵn, chỉ thiếu route).
2. **RBAC-1** — viết dependency phân quyền resource (chặn trước khi làm route Workspace/Project/Task).
3. **WS-1 → PRJ-1 → TASK-1..5 → LBL → CMT** — build route theo thứ tự phụ thuộc.
4. **CACHE-1/2 + DOCK-1 (Redis)** — thêm redis vào deps + compose, rồi cache route list task.
5. **BG-1** — background email khi assign task.
6. **LOG-1, MW-1, DOC-1, QA-1** — hoàn thiện chất lượng & vận hành.
