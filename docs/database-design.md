# TaskHub — Database Design

## 1. Tổng quan

TaskHub là hệ thống quản lý công việc đa workspace. Database được thiết kế theo hướng **multi-tenant theo Workspace**, với phân quyền RBAC (ADMIN / OWNER / EDITOR / VIEWER) áp dụng ở cả cấp hệ thống lẫn cấp workspace.

**Tech stack:** MySQL 8 / PostgreSQL 16 · SQLAlchemy 2.x async · Alembic · UUID v4 primary keys

---

## 2. Entities & Fields

### 2.1 `users`
Tài khoản người dùng hệ thống.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `id` | UUID | PK | |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Dùng để đăng nhập |
| `full_name` | VARCHAR(255) | | |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt hash |
| `role` | ENUM | NOT NULL, default `MEMBER` | `ADMIN` \| `MEMBER` — role cấp hệ thống |
| `is_superuser` | BOOLEAN | NOT NULL, default `false` | Bypass toàn bộ permission check |
| `is_active` | BOOLEAN | NOT NULL, default `true` | Soft-disable account |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

### 2.2 `refresh_tokens`
Lưu trữ refresh token để hỗ trợ logout / revoke.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK `users.id` CASCADE DELETE | |
| `token_hash` | VARCHAR(255) | UNIQUE, NOT NULL | SHA-256 của raw token |
| `expires_at` | TIMESTAMPTZ | NOT NULL | |
| `revoked_at` | TIMESTAMPTZ | | NULL = còn hiệu lực |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

### 2.3 `workspaces`
Đơn vị tổ chức cấp cao nhất.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `id` | UUID | PK | |
| `name` | VARCHAR(255) | NOT NULL | |
| `owner_id` | UUID | FK `users.id` NOT NULL | Người tạo workspace |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

### 2.4 `workspace_members`
Bảng join nhiều-nhiều giữa Workspace và User, kèm role.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `workspace_id` | UUID | PK, FK `workspaces.id` CASCADE DELETE | |
| `user_id` | UUID | PK, FK `users.id` CASCADE DELETE | |
| `role` | ENUM | NOT NULL | `OWNER` \| `EDITOR` \| `VIEWER` |
| `joined_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

> Composite PK `(workspace_id, user_id)`. Owner của workspace luôn có bản ghi ở đây với role = `OWNER`.

### 2.5 `projects`
Project thuộc một workspace.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `id` | UUID | PK | |
| `workspace_id` | UUID | FK `workspaces.id` CASCADE DELETE, NOT NULL | |
| `name` | VARCHAR(255) | NOT NULL | |
| `description` | TEXT | | |
| `status` | ENUM | NOT NULL, default `ACTIVE` | `ACTIVE` \| `ARCHIVED` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

### 2.6 `tasks`
Đơn vị công việc thuộc một project.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `id` | UUID | PK | |
| `project_id` | UUID | FK `projects.id` CASCADE DELETE, NOT NULL | |
| `assignee_id` | UUID | FK `users.id` SET NULL | Người được giao (nullable) |
| `created_by` | UUID | FK `users.id` NOT NULL | Người tạo task |
| `title` | VARCHAR(500) | NOT NULL | |
| `description` | TEXT | | |
| `status` | ENUM | NOT NULL, default `TODO` | `TODO` \| `IN_PROGRESS` \| `IN_REVIEW` \| `DONE` |
| `priority` | ENUM | NOT NULL, default `MEDIUM` | `LOW` \| `MEDIUM` \| `HIGH` \| `URGENT` |
| `due_date` | DATE | | |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

### 2.7 `labels`
Nhãn phân loại task, scoped theo project.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `id` | UUID | PK | |
| `project_id` | UUID | FK `projects.id` CASCADE DELETE, NOT NULL | |
| `name` | VARCHAR(100) | NOT NULL | |
| `color` | VARCHAR(7) | NOT NULL | Hex color, ví dụ `#FF5733` |

> UNIQUE `(project_id, name)` — tên label không trùng trong cùng project.

### 2.8 `task_labels`
Bảng join nhiều-nhiều Task ↔ Label.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `task_id` | UUID | PK, FK `tasks.id` CASCADE DELETE | |
| `label_id` | UUID | PK, FK `labels.id` CASCADE DELETE | |

> Composite PK `(task_id, label_id)`.

### 2.9 `comments`
Bình luận trên task.

| Column | Type | Constraint | Mô tả |
|--------|------|-----------|-------|
| `id` | UUID | PK | |
| `task_id` | UUID | FK `tasks.id` CASCADE DELETE, NOT NULL | |
| `author_id` | UUID | FK `users.id` NOT NULL | |
| `content` | TEXT | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` | |

---

## 3. Relationships

```
users ────────────────── 1:N ── workspaces          (owner_id)
users ────────────────── M:N ── workspaces          (via workspace_members)
users ────────────────── 1:N ── refresh_tokens
workspaces ──────────── 1:N ── projects
projects ────────────── 1:N ── tasks
projects ────────────── 1:N ── labels
tasks ───────────────── M:N ── labels               (via task_labels)
tasks ───────────────── 1:N ── comments
users ────────────────── 1:N ── tasks               (assignee_id, created_by)
users ────────────────── 1:N ── comments            (author_id)
```

---

## 4. RBAC Permission Matrix

| Action | ADMIN (system) | OWNER | EDITOR | VIEWER |
|--------|:-:|:-:|:-:|:-:|
| Manage workspace | ✓ | ✓ | ✗ | ✗ |
| Invite / remove members | ✓ | ✓ | ✗ | ✗ |
| Create / delete project | ✓ | ✓ | ✗ | ✗ |
| Archive project | ✓ | ✓ | ✗ | ✗ |
| Create / edit / delete task | ✓ | ✓ | ✓ | ✗ |
| Assign task | ✓ | ✓ | ✓ | ✗ |
| Add / remove label | ✓ | ✓ | ✓ | ✗ |
| Add comment | ✓ | ✓ | ✓ | ✗ |
| View tasks, comments | ✓ | ✓ | ✓ | ✓ |
| Delete own comment | ✓ | ✓ | ✓ (own) | ✓ (own) |

---

## 5. Index Strategy

| Table | Index | Lý do |
|-------|-------|-------|
| `users` | `idx_users_email` (UNIQUE) | Login lookup |
| `refresh_tokens` | `idx_rt_token_hash` (UNIQUE) | Token validation |
| `refresh_tokens` | `idx_rt_user_id` | Revoke all tokens for user |
| `workspace_members` | `idx_wm_user_id` | List user's workspaces |
| `projects` | `idx_projects_workspace_id` | List projects in workspace |
| `tasks` | `idx_tasks_project_id` | List tasks in project |
| `tasks` | `idx_tasks_assignee_id` | Filter by assignee |
| `tasks` | `idx_tasks_status_priority` | Filter + sort |
| `labels` | `idx_labels_project_id` | List labels in project |
| `comments` | `idx_comments_task_id` | List comments on task |

---

## 6. ERD — dbdiagram.io (DBML)

Paste đoạn DBML bên dưới vào [https://dbdiagram.io/d](https://dbdiagram.io/d) để xem ERD trực quan.

```dbml
// TaskHub — Task Management System
// Paste into https://dbdiagram.io/d

Table users {
  id          varchar(36)  [pk, note: "UUID v4"]
  email       varchar(255) [not null, unique]
  full_name   varchar(255)
  hashed_password varchar(255) [not null]
  role        varchar(10)  [not null, default: "MEMBER", note: "ADMIN | MEMBER"]
  is_superuser boolean     [not null, default: false]
  is_active   boolean      [not null, default: true]
  created_at  timestamp    [not null, default: `now()`]
  updated_at  timestamp    [not null, default: `now()`]

  indexes {
    email [unique, name: "idx_users_email"]
  }
}

Table refresh_tokens {
  id          varchar(36)  [pk, note: "UUID v4"]
  user_id     varchar(36)  [not null, ref: > users.id]
  token_hash  varchar(255) [not null, unique]
  expires_at  timestamp    [not null]
  revoked_at  timestamp    [note: "NULL = active"]
  created_at  timestamp    [not null, default: `now()`]

  indexes {
    token_hash [unique, name: "idx_rt_token_hash"]
    user_id    [name: "idx_rt_user_id"]
  }
}

Table workspaces {
  id         varchar(36)  [pk, note: "UUID v4"]
  name       varchar(255) [not null]
  owner_id   varchar(36)  [not null, ref: > users.id]
  created_at timestamp    [not null, default: `now()`]
  updated_at timestamp    [not null, default: `now()`]
}

Table workspace_members {
  workspace_id varchar(36) [not null, ref: > workspaces.id]
  user_id      varchar(36) [not null, ref: > users.id]
  role         varchar(10) [not null, note: "OWNER | EDITOR | VIEWER"]
  joined_at    timestamp   [not null, default: `now()`]

  indexes {
    (workspace_id, user_id) [pk]
    user_id [name: "idx_wm_user_id"]
  }
}

Table projects {
  id           varchar(36)  [pk, note: "UUID v4"]
  workspace_id varchar(36)  [not null, ref: > workspaces.id]
  name         varchar(255) [not null]
  description  text
  status       varchar(10)  [not null, default: "ACTIVE", note: "ACTIVE | ARCHIVED"]
  created_at   timestamp    [not null, default: `now()`]
  updated_at   timestamp    [not null, default: `now()`]

  indexes {
    workspace_id [name: "idx_projects_workspace_id"]
  }
}

Table tasks {
  id           varchar(36)  [pk, note: "UUID v4"]
  project_id   varchar(36)  [not null, ref: > projects.id]
  assignee_id  varchar(36)  [ref: > users.id, note: "nullable — SET NULL on user delete"]
  created_by   varchar(36)  [not null, ref: > users.id]
  title        varchar(500) [not null]
  description  text
  status       varchar(15)  [not null, default: "TODO", note: "TODO | IN_PROGRESS | IN_REVIEW | DONE"]
  priority     varchar(10)  [not null, default: "MEDIUM", note: "LOW | MEDIUM | HIGH | URGENT"]
  due_date     date
  created_at   timestamp    [not null, default: `now()`]
  updated_at   timestamp    [not null, default: `now()`]

  indexes {
    project_id              [name: "idx_tasks_project_id"]
    assignee_id             [name: "idx_tasks_assignee_id"]
    (status, priority)      [name: "idx_tasks_status_priority"]
  }
}

Table labels {
  id         varchar(36)  [pk, note: "UUID v4"]
  project_id varchar(36)  [not null, ref: > projects.id]
  name       varchar(100) [not null]
  color      varchar(7)   [not null, note: "Hex color e.g. #FF5733"]

  indexes {
    project_id [name: "idx_labels_project_id"]
    (project_id, name) [unique, name: "uq_labels_project_name"]
  }
}

Table task_labels {
  task_id  varchar(36) [not null, ref: > tasks.id]
  label_id varchar(36) [not null, ref: > labels.id]

  indexes {
    (task_id, label_id) [pk]
  }
}

Table comments {
  id         varchar(36) [pk, note: "UUID v4"]
  task_id    varchar(36) [not null, ref: > tasks.id]
  author_id  varchar(36) [not null, ref: > users.id]
  content    text        [not null]
  created_at timestamp   [not null, default: `now()`]

  indexes {
    task_id [name: "idx_comments_task_id"]
  }
}
```

---

## 7. SQLAlchemy Model Design (tham khảo)

### Enums

```python
import enum

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"

class WorkspaceMemberRole(str, enum.Enum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"

class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"
```

### Base & Mixins

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from sqlmodel import Field, SQLModel

def uuid_pk() -> uuid.UUID:
    return uuid.uuid4()

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class TimestampMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": func.now()},
        nullable=False,
    )
```

### Core Models (skeleton)

```python
class User(TimestampMixin, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    hashed_password: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.MEMBER)
    is_superuser: bool = Field(default=False)
    is_active: bool = Field(default=True)

    # relationships
    owned_workspaces: list["Workspace"] = Relationship(back_populates="owner")
    workspace_memberships: list["WorkspaceMember"] = Relationship(back_populates="user")
    assigned_tasks: list["Task"] = Relationship(
        back_populates="assignee",
        sa_relationship_kwargs={"foreign_keys": "[Task.assignee_id]"},
    )
    created_tasks: list["Task"] = Relationship(
        back_populates="creator",
        sa_relationship_kwargs={"foreign_keys": "[Task.created_by]"},
    )
    comments: list["Comment"] = Relationship(back_populates="author")
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user", cascade_delete=True
    )


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    token_hash: str = Field(unique=True, max_length=255)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    revoked_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))

    user: User | None = Relationship(back_populates="refresh_tokens")


class Workspace(TimestampMixin, table=True):
    __tablename__ = "workspaces"
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    name: str = Field(max_length=255)
    owner_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    owner: User | None = Relationship(back_populates="owned_workspaces")
    members: list["WorkspaceMember"] = Relationship(
        back_populates="workspace", cascade_delete=True
    )
    projects: list["Project"] = Relationship(
        back_populates="workspace", cascade_delete=True
    )


class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "workspace_members"
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", primary_key=True, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", primary_key=True, ondelete="CASCADE"
    )
    role: WorkspaceMemberRole = Field(default=WorkspaceMemberRole.VIEWER)
    joined_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))

    workspace: Workspace | None = Relationship(back_populates="members")
    user: User | None = Relationship(back_populates="workspace_memberships")


class Project(TimestampMixin, table=True):
    __tablename__ = "projects"
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False, ondelete="CASCADE"
    )
    name: str = Field(max_length=255)
    description: str | None = Field(default=None)
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)

    workspace: Workspace | None = Relationship(back_populates="projects")
    tasks: list["Task"] = Relationship(back_populates="project", cascade_delete=True)
    labels: list["Label"] = Relationship(back_populates="project", cascade_delete=True)


class Task(TimestampMixin, table=True):
    __tablename__ = "tasks"
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE"
    )
    assignee_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    title: str = Field(max_length=500)
    description: str | None = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    due_date: date | None = Field(default=None)

    project: Project | None = Relationship(back_populates="tasks")
    assignee: User | None = Relationship(
        back_populates="assigned_tasks",
        sa_relationship_kwargs={"foreign_keys": "[Task.assignee_id]"},
    )
    creator: User | None = Relationship(
        back_populates="created_tasks",
        sa_relationship_kwargs={"foreign_keys": "[Task.created_by]"},
    )
    labels: list["Label"] = Relationship(back_populates="tasks", link_model=TaskLabel)
    comments: list["Comment"] = Relationship(
        back_populates="task", cascade_delete=True
    )


class TaskLabel(SQLModel, table=True):
    __tablename__ = "task_labels"
    task_id: uuid.UUID = Field(
        foreign_key="tasks.id", primary_key=True, ondelete="CASCADE"
    )
    label_id: uuid.UUID = Field(
        foreign_key="labels.id", primary_key=True, ondelete="CASCADE"
    )


class Label(SQLModel, table=True):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("project_id", "name"),)
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE"
    )
    name: str = Field(max_length=100)
    color: str = Field(max_length=7)

    project: Project | None = Relationship(back_populates="labels")
    tasks: list["Task"] = Relationship(back_populates="labels", link_model=TaskLabel)


class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    task_id: uuid.UUID = Field(
        foreign_key="tasks.id", nullable=False, ondelete="CASCADE"
    )
    author_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    content: str
    created_at: datetime = Field(
        default_factory=utcnow, sa_type=DateTime(timezone=True)
    )

    task: Task | None = Relationship(back_populates="comments")
    author: User | None = Relationship(back_populates="comments")
```

---

## 8. Cascade Delete Summary

| Quan hệ | Hành vi khi xóa parent |
|---------|----------------------|
| User → RefreshTokens | CASCADE DELETE |
| Workspace → WorkspaceMembers | CASCADE DELETE |
| Workspace → Projects | CASCADE DELETE |
| Project → Tasks | CASCADE DELETE |
| Project → Labels | CASCADE DELETE |
| Task → Comments | CASCADE DELETE |
| Task → TaskLabels | CASCADE DELETE |
| Label → TaskLabels | CASCADE DELETE |
| User → Tasks (assignee) | SET NULL (`assignee_id`) |

---

## 9. Notes

- **UUID v4** được dùng cho tất cả PK thay vì auto-increment integer để tránh enumeration attack và hỗ trợ distributed insert.
- **`refresh_tokens.token_hash`** lưu SHA-256 của raw token — không lưu raw token để giảm impact nếu DB bị lộ.
- **Redis cache key** cho task list: `tasks:project:{project_id}:page:{page}:limit:{limit}:status:{status}:priority:{priority}:assignee:{assignee_id}` — invalidate toàn bộ key theo prefix `tasks:project:{project_id}:*` khi có thay đổi task.
- **`workspace_members.role = OWNER`** phải luôn tồn tại cho owner — khi transfer ownership cần transaction update cả `workspaces.owner_id` và bản ghi trong `workspace_members`.

---

## 10. Implementation Guide

Phần này ghi lại toàn bộ các bước đã thực hiện để implement database design thành code thực tế, bao gồm lý do đằng sau mỗi quyết định.

---

### 10.1 Chuẩn bị cấu trúc thư mục

```bash
# Di chuyển file models.py cũ (template) ra khỏi đường đi
mv backend/app/models.py backend/app/_legacy_models.py

# Tạo package mới cho models và repositories
mkdir -p backend/app/models
mkdir -p backend/app/repositories

# Archive toàn bộ migration cũ (dành cho template User/Item)
mkdir -p backend/app/alembic/versions/_archive
mv backend/app/alembic/versions/*.py backend/app/alembic/versions/_archive/
```

**Tại sao?**

- `models.py` của template chứa `User` và `Item` (template boilerplate), không liên quan đến TaskHub. Giữ lại trong `_legacy_models.py` thay vì xóa hẳn để tham khảo các Pydantic schema generic (`Token`, `Message`) khi cần.
- Python không thể có cả `app/models.py` lẫn `app/models/` (package) cùng lúc — phải chọn một. Package (directory) cho phép chia nhỏ model theo từng domain, dễ maintain hơn file monolithic.
- Các migration cũ tạo bảng `user` và `item` (template). Nếu để nguyên, Alembic sẽ coi chúng là "đã apply" và không tạo bảng TaskHub. Archive để bắt đầu sạch với revision chain mới.

---

### 10.2 Model Layer

#### Cấu trúc file

```
backend/app/models/
├── __init__.py       # Re-export tất cả, Alembic đọc SQLModel.metadata từ đây
├── enums.py          # Python enums cho tất cả ENUM columns
├── base.py           # Helper functions dùng chung
├── user.py           # User, RefreshToken
├── workspace.py      # Workspace, WorkspaceMember
├── project.py        # Project
├── task.py           # Task, Label, TaskLabel
└── comment.py        # Comment
```

#### `enums.py` — Tại sao dùng `str` enum?

```python
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
```

Kế thừa `str` (thay vì chỉ `enum.Enum`) vì:
1. Pydantic v2 serialize trực tiếp thành chuỗi JSON — không cần `.value`.
2. SQLAlchemy lưu vào DB dưới dạng `VARCHAR` — không cần PostgreSQL ENUM type (portable hơn, dễ thêm value mới).
3. So sánh string trong query (`Task.status == "TODO"`) hoạt động tự nhiên.

#### `base.py` — Factory functions thay vì Mixin

```python
def created_at_col() -> Column:
    return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

def updated_at_col() -> Column:
    return Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

**Tại sao dùng function thay vì `TimestampMixin`?**

SQLAlchemy yêu cầu mỗi `Column` object phải thuộc về đúng một `Table`. Nếu dùng mixin với `sa_column=Column(...)` trực tiếp, nhiều model chia sẻ **cùng một** Column object → SQLAlchemy raise lỗi `Column already attached`. Gọi function mỗi lần tạo ra Column object mới → an toàn.

`server_default=func.now()` — DB tự điền timestamp khi INSERT (không phụ thuộc vào Python time).  
`onupdate=func.now()` trong `updated_at_col()` — SQLAlchemy tự thêm `updated_at = now()` vào mọi UPDATE statement.

#### `user.py` — Tại sao tách `RefreshToken` thành bảng riêng?

```python
class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    token_hash: str = Field(sa_column=Column(String(255), unique=True, nullable=False, index=True))
    revoked_at: datetime | None = Field(default=None, ...)
```

Feature **Logout** yêu cầu revoke refresh token. Có 2 cách:
- **Blocklist trong Redis** — nhanh nhưng mất data khi Redis restart.
- **Lưu DB** — bền vững, hỗ trợ "đăng xuất tất cả thiết bị" (`revoke_all_for_user`).

Lưu `token_hash` (SHA-256) thay vì raw token — nếu DB bị lộ, attacker không dùng được hash để forge token.

#### `task.py` — Xử lý 2 FK tới cùng bảng `users`

```python
class Task(SQLModel, table=True):
    assignee_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", nullable=True
    )
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
```

`Task` có 2 FK đến `users` (`assignee_id` và `created_by`). SQLModel's `Relationship()` không tự phân biệt được khi có ambiguity như này — cần khai báo `sa_relationship_kwargs={"foreign_keys": [...]}` explicit. Để tránh phức tạp, **không khai báo Python-level `Relationship()`** cho 2 FK này. Repositories xử lý bằng explicit `select()` + `JOIN` khi cần load user data.

`ondelete="SET NULL"` cho `assignee_id` — xóa user không xóa task, chỉ unassign. `created_by` không có `ondelete` → DB sẽ từ chối xóa user nếu còn task do họ tạo (đây là intentional constraint).

#### `models/__init__.py` — Tại sao import thứ tự quan trọng?

```python
# Import theo thứ tự dependency
from app.models.user import RefreshToken, User        # không phụ thuộc gì
from app.models.workspace import Workspace, WorkspaceMember  # phụ thuộc users.id FK
from app.models.project import Project                # phụ thuộc workspaces.id FK
from app.models.task import Label, Task, TaskLabel    # phụ thuộc projects.id + users.id FK
from app.models.comment import Comment                # phụ thuộc tasks.id + users.id FK
```

SQLModel resolve FK string references (`foreign_key="users.id"`) tại **import time** thông qua SQLAlchemy's metadata registry. Nếu `User` chưa được import trước khi `Workspace` được load, FK `workspaces.owner_id → users.id` không tìm thấy table `users` → `NoReferencedTableError`. Import theo thứ tự dependency đảm bảo mọi referenced table đã được register trước.

`alembic/env.py` import từ `app.models` (package này) → `SQLModel.metadata` chứa đủ schema để autogenerate.

---

### 10.3 Repository Pattern

#### Cấu trúc file

```
backend/app/repositories/
├── __init__.py       # Singleton instances sẵn dùng
├── base.py           # BaseRepository[ModelT] + Page[T]
├── user.py           # UserRepository, RefreshTokenRepository
├── workspace.py      # WorkspaceRepository, WorkspaceMemberRepository
├── project.py        # ProjectRepository
├── task.py           # TaskRepository (filtering + label management)
├── label.py          # LabelRepository
└── comment.py        # CommentRepository
```

#### `base.py` — Thiết kế `Page[T]` và `BaseRepository[ModelT]`

**`Page[T]` — Generic dataclass:**

```python
@dataclass
class Page(Generic[ModelT]):
    items: list[ModelT]
    total: int
    page: int
    limit: int
    pages: int = field(init=False)   # tính tự động

    def __post_init__(self) -> None:
        self.pages = math.ceil(self.total / self.limit) if self.limit else 0

    @property
    def has_next(self) -> bool: ...
    @property
    def has_prev(self) -> bool: ...
```

`@dataclass` + `field(init=False)` cho `pages` — caller không truyền `pages`, nó tự tính từ `total / limit`. `has_next` / `has_prev` giúp API response trả về navigation hints mà không cần tính lại ở route layer.

**`BaseRepository[ModelT]` — Generic với `ClassVar`:**

```python
class BaseRepository(Generic[ModelT]):
    model: ClassVar[type[Any]]  # type: ignore[misc]
```

`ClassVar` khai báo `model` là attribute của *class*, không phải instance. Subclass gán cụ thể:
```python
class UserRepository(BaseRepository[User]):
    model = User
```

`# type: ignore[misc]` cần vì mypy strict không support `ClassVar` với Generic type tốt — đây là known limitation của mypy, không phải lỗi logic.

**Tại sao dùng `flush()` thay vì `commit()` trong write operations?**

```python
async def create(self, session: AsyncSession, data: dict[str, Any]) -> ModelT:
    db_obj = self.model(**data)
    session.add(db_obj)
    await session.flush()     # ← không phải commit()
    await session.refresh(db_obj)
    return db_obj
```

- `flush()` — gửi SQL xuống DB nhưng **chưa commit transaction**. ID được assign (nếu DB generate), DB constraint được kiểm tra ngay.
- `commit()` sẽ được gọi ở **session lifecycle** (`get_async_session()` trong `core/db.py`), không phải trong repository.
- Lý do: Một request handler có thể gọi nhiều repository method — tất cả nằm trong cùng transaction. Nếu repository tự `commit()`, mỗi write là 1 transaction riêng → không thể rollback toàn bộ nếu có lỗi ở bước sau.

**`refresh()` sau write:**

```python
await session.refresh(db_obj)
```

Sau `flush()`, các server-side default (`created_at`, `updated_at`, sequences) chỉ tồn tại trong DB. `refresh()` re-read từ DB → Python object có giá trị đầy đủ để trả về response.

#### `task.py` — Filtering với dynamic WHERE clauses

```python
async def list_by_project(
    self, session: AsyncSession, project_id: UUID, *,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: UUID | None = None,
) -> Page[Task]:
    base = select(Task).where(Task.project_id == project_id)
    count_q = select(func.count()).select_from(Task).where(...)

    if status is not None:
        base = base.where(Task.status == status.value)
        count_q = count_q.where(Task.status == status.value)
    # ... tương tự priority, assignee_id
```

Filter được build động thay vì một query cứng — `None` nghĩa là "không filter theo trường này". Cùng một `count_q` với cùng filter được chạy để lấy `total` chính xác cho `Page`. Không thể tái dùng 1 query vì `COUNT(*)` và `SELECT *` trả về result set khác nhau.

#### `repositories/__init__.py` — Singleton pattern

```python
users = UserRepository()
refresh_tokens = RefreshTokenRepository()
workspaces = WorkspaceRepository()
# ...
```

Repository không lưu state (session được truyền vào mỗi method call) → an toàn để dùng singleton. Route handlers import trực tiếp:

```python
from app.repositories import users, tasks

user = await users.get_by_email(session, email)
```

Không cần `UserRepository()` ở mỗi nơi, không cần DI container.

---

### 10.4 Async Database Layer

**File:** `backend/app/core/db.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Giải thích từng option:**

| Option | Giá trị | Lý do |
|--------|---------|-------|
| `echo=False` | False | Không log SQL ra stdout (bật `True` khi debug) |
| `pool_pre_ping=True` | True | Test connection trước khi dùng — tránh "connection closed" sau idle timeout |
| `expire_on_commit=False` | False | Sau `commit()`, không expire attributes — tránh lazy load lỗi trong async |
| `autocommit=False` | False | Mọi thay đổi phải explicit commit |
| `autoflush=False` | False | Repositories tự gọi `flush()` — tránh flush ngoài ý muốn |

**Transaction lifecycle trong `get_async_session()`:**

```
request đến
    → session mở
    → yield session  ←── route handler chạy, gọi repositories
    → commit()       ←── nếu không có exception
    → session đóng
    
exception xảy ra
    → rollback()     ←── undo toàn bộ thay đổi trong request
    → session đóng
    → re-raise để FastAPI trả về 500
```

**Tại sao dùng Connection URI `postgresql+psycopg`?**

Driver `psycopg` (psycopg3) hỗ trợ async natively với scheme `postgresql+psycopg` — không cần cài thêm `asyncpg`. `pyproject.toml` đã có `psycopg[binary]`, không cần thêm dependency.

---

### 10.5 Alembic Migration

#### Cập nhật `alembic/env.py`

```python
# Import tất cả models để SQLModel.metadata có đủ schema
from app.models import SQLModel  # noqa: E402
from app.core.config import settings  # noqa: E402

target_metadata = SQLModel.metadata
```

**Tại sao import `app.models` thay vì từng model riêng?**

`app/models/__init__.py` import tất cả table classes theo đúng thứ tự dependency. Chỉ cần `from app.models import SQLModel` là đủ để `SQLModel.metadata` chứa toàn bộ 9 bảng.

**Alembic vẫn chạy sync dù app dùng async:**

Alembic migration script không cần async — nó chạy trong CLI, không trong event loop của FastAPI. `engine_from_config` tạo sync engine (không phải `create_async_engine`). DB driver `psycopg` hỗ trợ cả sync lẫn async với cùng URI.

#### Migration file: `0001_initial_taskhub_schema.py`

```python
revision = "0001"
down_revision = None   # Đây là root — không phụ thuộc migration nào trước
```

**Tại sao `down_revision = None`?**

Các migration cũ (template) đã được archive. Bắt đầu fresh chain với một "initial" migration duy nhất biểu diễn toàn bộ schema của TaskHub.

**Thứ tự `create_table` trong `upgrade()`:**

```
1. users           (không phụ thuộc)
2. refresh_tokens  (FK → users)
3. workspaces      (FK → users)
4. workspace_members (FK → workspaces, users)
5. projects        (FK → workspaces)
6. tasks           (FK → projects, users × 2)
7. labels          (FK → projects)
8. task_labels     (FK → tasks, labels)
9. comments        (FK → tasks, users)
```

Phải tạo parent table trước child table — vì FK constraint cần referenced table tồn tại. `downgrade()` drop theo thứ tự **ngược lại** vì lý do tương tự.

**`ondelete` trong FK constraints:**

```python
sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"),
sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
```

- `CASCADE` — xóa workspace → tự xóa tất cả projects, tasks, comments, labels của workspace đó.
- `SET NULL` — xóa user → task không bị xóa, chỉ `assignee_id` thành NULL (task vẫn tồn tại).
- Không có `ondelete` — DB sẽ từ chối `DELETE` nếu còn FK reference (ví dụ: `tasks.created_by → users.id`).

**`server_default` trong migration vs Python model:**

```python
# Migration:
sa.Column("role", sa.String(10), nullable=False, server_default="MEMBER")

# Model:
role: str = Field(default=UserRole.MEMBER, sa_column=Column(String(10), ...))
```

- `server_default` — DB tự điền khi INSERT không truyền giá trị (ví dụ: seed script, raw SQL).
- `default` trong Field — Python điền trước khi gửi xuống DB.
- Cả hai cùng nhau đảm bảo default đúng ở mọi access path.

---

### 10.6 Kiểm tra sau khi implement

#### Verify import tất cả models và repositories

```bash
cd backend
uv run python -c "
from app.models import (
    User, RefreshToken, Workspace, WorkspaceMember,
    Project, Task, Label, TaskLabel, Comment
)
from app.repositories import users, tasks, projects, comments, Page
print('Tables:', [m.__tablename__ for m in [
    User, RefreshToken, Workspace, WorkspaceMember,
    Project, Task, Label, TaskLabel, Comment
]])
print('Page fields:', list(Page.__dataclass_fields__.keys()))
"
```

Kết quả mong đợi:
```
Tables: ['users', 'refresh_tokens', 'workspaces', 'workspace_members', 
         'projects', 'tasks', 'labels', 'task_labels', 'comments']
Page fields: ['items', 'total', 'page', 'limit', 'pages']
```

**Tại sao chạy lệnh này?** Kiểm tra không có circular import, FK reference hợp lệ, và toàn bộ package structure đúng — trước khi chạy migration với DB thật.

#### Verify Alembic nhận ra migration

```bash
cd backend
uv run alembic history
```

Kết quả mong đợi:
```
<base> -> 0001 (head), Initial TaskHub schema
```

Nếu không thấy output này: kiểm tra `alembic.ini` → `script_location = app/alembic` và `env.py` có import models chưa.

#### Chạy migration (khi DB đang chạy)

```bash
# Trong docker-compose hoặc sau khi có DB
uv run alembic upgrade head
```

- `upgrade head` — apply tất cả migration chưa chạy tới revision mới nhất (`0001`).
- Alembic tạo bảng `alembic_version` trong DB để track revision hiện tại.

#### Rollback migration

```bash
uv run alembic downgrade base
```

- `downgrade base` — chạy `downgrade()` của tất cả revision theo thứ tự ngược → xóa toàn bộ bảng TaskHub.
- Dùng khi cần reset DB để test migration từ đầu.

#### Generate migration mới sau khi sửa model

```bash
uv run alembic revision --autogenerate -m "add column X to table Y"
```

- `--autogenerate` — Alembic so sánh `SQLModel.metadata` (Python models) với schema hiện tại trong DB, tự sinh migration code.
- Luôn review file được tạo ra trước khi chạy — autogenerate có thể miss một số thay đổi (ví dụ: server_default, index name).

---

### 10.7 Cách sử dụng Repositories trong Route Handler

```python
# Ví dụ: route lấy task list với filtering và caching
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.models.enums import TaskStatus, TaskPriority
from app.repositories import tasks

router = APIRouter()

@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: uuid.UUID,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_async_session),
):
    result = await tasks.list_by_project(
        session,
        project_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        page=page,
        limit=limit,
    )
    # result.items, result.total, result.pages, result.has_next, result.has_prev
    return result
```

Session được inject qua `Depends(get_async_session)` — FastAPI gọi `get_async_session()` generator, yield session vào route, tự động `commit()` sau khi response được trả về hoặc `rollback()` nếu có exception.

---

### 10.8 File tree sau khi implement

```
backend/
├── app/
│   ├── _legacy_models.py          # Template boilerplate (archived)
│   ├── alembic/
│   │   ├── env.py                 # Updated: import từ app.models
│   │   └── versions/
│   │       ├── _archive/          # Migration cũ của template
│   │       └── 0001_initial_taskhub_schema.py  # Migration TaskHub
│   ├── core/
│   │   └── db.py                  # Updated: async engine + session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # Column factory functions
│   │   ├── enums.py               # Tất cả enums
│   │   ├── user.py                # User, RefreshToken
│   │   ├── workspace.py           # Workspace, WorkspaceMember
│   │   ├── project.py             # Project
│   │   ├── task.py                # Task, Label, TaskLabel
│   │   └── comment.py             # Comment
│   └── repositories/
│       ├── __init__.py            # Singleton instances
│       ├── base.py                # BaseRepository[T] + Page[T]
│       ├── user.py
│       ├── workspace.py
│       ├── project.py
│       ├── task.py                # Filtering + label attach/detach
│       ├── label.py
│       └── comment.py
└── pyproject.toml                 # psycopg[binary] — driver cho cả sync + async
```
