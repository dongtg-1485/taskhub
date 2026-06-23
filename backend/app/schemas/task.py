import uuid
from datetime import date, datetime

from sqlmodel import Field, SQLModel
from sqlalchemy import Date

from app.models.enums import (
    TaskStatus,
    TaskPriority,
)

class TaskResponseBase(SQLModel):
    """Schema cơ bản cho Task response."""

    id: uuid.UUID
    project_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    created_by: uuid.UUID
    title: str = Field(max_length=500)
    description: str | None = None
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority | None = None
    due_date: date | None = Field(default=None, sa_type=Date())
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskResponse(TaskResponseBase):
    """Schema trả về cho client khi GET Task."""

    pass


class TasksResponse(SQLModel):
    """Schema trả về danh sách Task có kèm tổng số (dùng cho phân trang)."""

    data: list[TaskResponse]
    count: int


class CreateTaskRequest(SQLModel):
    """Schema dùng để tạo mới Task."""

    assignee_id: uuid.UUID | None = None
    title: str = Field(max_length=500)
    description: str | None = None
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    due_date: date | None = Field(default=None, sa_type=Date())

class UpdateTaskRequest(SQLModel):
    """Schema dùng để cập nhật Task."""

    assignee_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = Field(default=None, sa_type=Date())