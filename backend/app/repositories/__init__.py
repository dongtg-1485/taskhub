from app.repositories.base import Page  # noqa: F401
from app.repositories.comment import CommentRepository
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.user import RefreshTokenRepository, UserRepository
from app.repositories.workspace import WorkspaceMemberRepository, WorkspaceRepository

users = UserRepository()
refresh_tokens = RefreshTokenRepository()
workspaces = WorkspaceRepository()
workspace_members = WorkspaceMemberRepository()
projects = ProjectRepository()
tasks = TaskRepository()
labels = LabelRepository()
comments = CommentRepository()

__all__ = [
    "Page",
    "users",
    "refresh_tokens",
    "workspaces",
    "workspace_members",
    "projects",
    "tasks",
    "labels",
    "comments",
]
