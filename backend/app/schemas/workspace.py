import uuid
from datetime import datetime

from sqlmodel import SQLModel

from app.models.enums import WorkspaceMemberRole


class WorkspaceResponseBase(SQLModel):
    """Schema cơ bản cho Workspace response."""

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkspaceResponse(WorkspaceResponseBase):
    """Schema trả về cho client khi GET workspace."""

    pass


class WorkspacesResponse(SQLModel):
    """Schema trả về danh sách workspace có kèm tổng số (dùng cho phân trang)."""

    data: list[WorkspaceResponse]
    count: int


class CreateWorkspaceRequest(SQLModel):
    """Schema dùng để tạo mới workspace."""

    name: str


class InviteMemberRequest(SQLModel):
    """Schema dùng để mời một user vào workspace với role cụ thể."""

    user_id: uuid.UUID
    role: WorkspaceMemberRole


class InviteMembersResponse(SQLModel):
    """Schema trả về danh sách user đã được mời vào workspace."""

    invited_members: list[uuid.UUID]


class WorkspaceMemberResponse(SQLModel):
    """Schema trả về thông tin một thành viên trong workspace."""

    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: WorkspaceMemberRole
    joined_at: datetime


class WorkspaceMembersResponse(SQLModel):
    """Schema trả về danh sách thành viên trong workspace có kèm tổng số."""

    data: list[WorkspaceMemberResponse]
    count: int
