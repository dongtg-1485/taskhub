import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import ProjectStatus


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False, ondelete="CASCADE"
    )
    name: str = Field(max_length=255)
    description: str | None = Field(default=None)
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())
    updated_at: Optional[datetime] = Field(default=None, sa_column=updated_at_col())

    workspace: Optional["Workspace"] = Relationship(back_populates="projects")  # type: ignore[name-defined]
    tasks: list["Task"] = Relationship(back_populates="project", cascade_delete=True)  # type: ignore[name-defined]
    labels: list["Label"] = Relationship(back_populates="project", cascade_delete=True)  # type: ignore[name-defined]
