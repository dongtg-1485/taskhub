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
    User,
    UserBase,
)
from app.models.workspace import (  # noqa: F401
    Workspace,
    WorkspaceMember,
)
from app.schemas.user import (  # noqa: F401
    CreateUserRequest,
    RegisterUserRequest,
    UpdateCurrentUserRequest,
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserResponse,
    UsersResponse,
)
from app.schemas.auth import RefreshTokenRequest, TokenResponse  # noqa: F401
from app.schemas.workspace import (  # noqa: F401
    CreateWorkspaceRequest,
    InviteMemberRequest,
    InviteMembersResponse,
    UpdateWorkspaceRequest,
    WorkspaceMemberResponse,
    WorkspaceMembersResponse,
    WorkspaceResponse,
    WorkspaceResponseBase,
    WorkspacesResponse,
)
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
    # Users (ORM)
    "User",
    "RefreshToken",
    "UserBase",
    # User schemas
    "CreateUserRequest",
    "RegisterUserRequest",
    "UpdateUserRequest",
    "UpdateCurrentUserRequest",
    "UpdatePasswordRequest",
    "UserResponse",
    "UsersResponse",
    # Auth schemas
    "TokenResponse",
    "RefreshTokenRequest",
    # Workspaces (ORM)
    "Workspace",
    "WorkspaceMember",
    # Workspace schemas
    "WorkspaceResponseBase",
    "WorkspaceResponse",
    "WorkspacesResponse",
    "CreateWorkspaceRequest",
    "UpdateWorkspaceRequest",
    "InviteMemberRequest",
    "InviteMembersResponse",
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
