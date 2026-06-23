# ruff: noqa: I001 — giữ nguyên thứ tự import theo phụ thuộc FK (không để isort sắp lại)
# Import theo thứ tự phụ thuộc FK để SQLModel.metadata được populated đúng thứ tự.
# Thứ tự: enums -> user -> workspace -> project -> task -> comment
# (mỗi model phụ thuộc FK vào model trước nó)
from app.models.enums import (  # noqa: F401
    ProjectStatus,
    TaskPriority,
    TaskStatus,
    UserRole,
    WorkspaceMemberRole,
)
from app.models.user import (  # noqa: F401
    RefreshToken,
    UpdatePassword,
    User,
    UserBase,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.models.auth import RefreshRequest, TokenPair  # noqa: F401
from app.models.workspace import (
    Workspace, 
    WorkspaceMember,
    WorkspaceBase,
    WorkspaceCreate,
    WorkspacePublic,
    WorkspacesPublic,
    WorkspaceMemberInvite,
    WorkspaceInvatedUsers,
)  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.task import Label, Task, TaskLabel  # noqa: F401
from app.models.comment import Comment  # noqa: F401

# Schema và model legacy (backward compat với các API route cũ chưa được migrate)
from app.models._schemas import (  # noqa: F401
    Item,
    ItemBase,
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
    Message,
    NewPassword,
    Token,
    TokenPayload,
)

from sqlmodel import SQLModel  # noqa: F401

__all__ = [
    "SQLModel",
    # Enums
    "UserRole",
    "WorkspaceMemberRole",
    "ProjectStatus",
    "TaskStatus",
    "TaskPriority",
    # Users
    "User",
    "RefreshToken",
    "UserBase",
    "UserCreate",
    "UserRegister",
    "UserUpdate",
    "UserUpdateMe",
    "UpdatePassword",
    "UserPublic",
    "UsersPublic",
    # Auth
    "TokenPair",
    "RefreshRequest",
    # Workspaces
    "Workspace",
    "WorkspaceMember",
    "WorkspaceBase",
    "WorkspaceCreate",
    "WorkspacePublic",
    "WorkspacesPublic",
    "WorkspaceMemberInvite",
    "WorkspaceInvatedUsers",
    # Projects
    "Project",
    # Tasks
    "Task",
    "Label",
    "TaskLabel",
    # Comments
    "Comment",
    # Legacy
    "Item",
    "ItemBase",
    "ItemCreate",
    "ItemUpdate",
    "ItemPublic",
    "ItemsPublic",
    "Message",
    "Token",
    "TokenPayload",
    "NewPassword",
]
