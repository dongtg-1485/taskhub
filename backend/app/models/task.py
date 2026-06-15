import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, UniqueConstraint
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import TaskPriority, TaskStatus


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
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_labels_project_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE"
    )
    name: str = Field(max_length=100)
    color: str = Field(max_length=7)

    project: Optional["Project"] = Relationship(back_populates="labels")  # type: ignore[name-defined]
    tasks: list["Task"] = Relationship(back_populates="labels", link_model=TaskLabel)


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
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
    due_date: date | None = Field(
        default=None, sa_type=Date()  # type: ignore[call-arg]
    )
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())
    updated_at: Optional[datetime] = Field(default=None, sa_column=updated_at_col())

    project: Optional["Project"] = Relationship(back_populates="tasks")  # type: ignore[name-defined]
    labels: list[Label] = Relationship(back_populates="tasks", link_model=TaskLabel)
    comments: list["Comment"] = Relationship(  # type: ignore[name-defined]
        back_populates="task", cascade_delete=True
    )
