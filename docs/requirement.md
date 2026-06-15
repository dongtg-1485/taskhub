# Requirement

### Tổng quan

| Hạng mục | Mô tả |
|----------|-------|
| **Tên project** | TaskHub — Hệ thống quản lý công việc (Task Management API) |
| **Domain** | Task management system: User, Workspace, Project, Task, Label, Comment, Notification |
| **Tech stack** | FastAPI 0.111+ \| SQLAlchemy 2.x async \| Alembic \| Pydantic v2 \| Redis 7 \| MySQL 8 (hoặc PostgreSQL 16) \| Docker |

### DB Schema (entities chính)

| # | Entity | Fields |
|:-:|--------|--------|
| 1 | **users** | `id`, `email`, `full_name`, `hashed_password`, `role` (ADMIN/MEMBER), `is_active`, `created_at` |
| 2 | **workspaces** | `id`, `name`, `owner_id`, `created_at` |
| 3 | **workspace_members** | `workspace_id`, `user_id`, `role` (OWNER/EDITOR/VIEWER) |
| 4 | **projects** | `id`, `workspace_id`, `name`, `description`, `status` (ACTIVE/ARCHIVED), `created_at` |
| 5 | **tasks** | `id`, `project_id`, `assignee_id`, `title`, `description`, `status` (TODO/IN_PROGRESS/IN_REVIEW/DONE), `priority` (LOW/MEDIUM/HIGH/URGENT), `due_date`, `created_by`, `created_at` |
| 6 | **labels** | `id`, `project_id`, `name`, `color` |
| 7 | **task_labels** | `task_id`, `label_id` |
| 8 | **comments** | `id`, `task_id`, `author_id`, `content`, `created_at` |

### Features (bắt buộc)

| # | Feature | Mô tả |
|:-:|---------|-------|
| 1 | **Auth** | Register, Login (JWT access + refresh token), Logout (revoke refresh token) |
| 2 | **User** | Get profile, Update profile (PATCH), Change password |
| 3 | **Workspace** | CRUD (owner only), Invite member, Remove member, Phân quyền theo role |
| 4 | **Project** | CRUD trong workspace, Archive project |
| 5 | **Task** | CRUD trong project, Assign task cho member, Chuyển status, Đặt priority & due_date |
| 6 | **Label** | CRUD (per project), Gán/bỏ label cho task |
| 7 | **Comment** | Thêm/xóa comment trên task |
| 8 | **Filtering & Pagination** | Lọc task theo status, priority, assignee; page + limit |
| 9 | **Caching** | Cache `GET /projects/{id}/tasks` với Redis, invalidate khi có thay đổi |
| 10 | **Background Task** | Gửi email notification khi được assign task |
| 11 | **RBAC** | Phân quyền ADMIN / OWNER / EDITOR / VIEWER đúng theo từng resource |
| 12 | **Swagger/ReDoc** | Đầy đủ, có Bearer auth scheme, document error responses |
| 13 | **Docker** | `docker compose up` chạy được toàn bộ stack (app + DB + Redis) |
| 14 | **Code Quality** | Ruff lint pass 100%, mypy không có error |

### API Endpoints (tham khảo)

**Auth:**
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

**User:**
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`

**Workspace:**
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{id}`
- `POST /api/v1/workspaces/{id}/members`
- `DELETE /api/v1/workspaces/{id}/members/{user_id}`

**Project & Task:**
- `POST /api/v1/workspaces/{id}/projects`
- `GET /api/v1/projects/{id}/tasks` *(filter + pagination + cache)*
- `POST /api/v1/projects/{id}/tasks`
- `PATCH /api/v1/tasks/{id}`
- `DELETE /api/v1/tasks/{id}`

**Label & Comment:**
- `POST /api/v1/tasks/{id}/labels/{label_id}`
- `POST /api/v1/tasks/{id}/comments`