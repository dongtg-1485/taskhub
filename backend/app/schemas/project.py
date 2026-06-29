import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.enums import ProjectStatus


class ProjectResponseBase(SQLModel):
    """Schema cơ bản cho Project response."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str = Field(max_length=255)
    description: str | None = Field(default=None)
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProjectResponse(ProjectResponseBase):
    """Schema trả về cho client khi GET Project."""

    pass


class ProjectsResponse(SQLModel):
    """Schema trả về danh sách Project có kèm tổng số (dùng cho phân trang)."""

    data: list[ProjectResponse]
    count: int


class CreateProjectRequest(SQLModel):
    """Schema dùng để tạo mới Project."""

    name: str = Field(max_length=255)
    description: str | None = Field(default=None)


class UpdateProjectRequest(SQLModel):
    """Schema dùng để cập nhật thông tin Project."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
