import uuid
from datetime import date, datetime

from sqlalchemy import Date
from sqlmodel import Field, SQLModel

from app.models.enums import (
    TaskPriority,
    TaskStatus,
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
    """Schema trả về danh sách Task có kèm metadata phân trang."""

    data: list[TaskResponse]
    count: int  # Tổng số record thỏa điều kiện lọc
    page: int  # Trang hiện tại (bắt đầu từ 1)
    limit: int  # Số record mỗi trang
    pages: int  # Tổng số trang


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
