# Import in FK dependency order so SQLModel.metadata is populated correctly
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
from app.models.workspace import Workspace, WorkspaceMember  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.task import Label, Task, TaskLabel  # noqa: F401
from app.models.comment import Comment  # noqa: F401

# Legacy schemas & Item model (backward compat with existing API routes)
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
    # Workspaces
    "Workspace",
    "WorkspaceMember",
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
