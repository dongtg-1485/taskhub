import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import WorkspaceMemberRole


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    owner_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())
    updated_at: Optional[datetime] = Field(default=None, sa_column=updated_at_col())

    owner: Optional["User"] = Relationship(back_populates="owned_workspaces")  # type: ignore[name-defined]
    members: list["WorkspaceMember"] = Relationship(
        back_populates="workspace", cascade_delete=True
    )
    projects: list["Project"] = Relationship(  # type: ignore[name-defined]
        back_populates="workspace", cascade_delete=True
    )


class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "workspace_members"

    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", primary_key=True, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", primary_key=True, ondelete="CASCADE"
    )
    role: WorkspaceMemberRole = Field(default=WorkspaceMemberRole.VIEWER)
    joined_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=DateTime(timezone=True),  # type: ignore[call-arg]
    )

    workspace: Optional[Workspace] = Relationship(back_populates="members")
    user: Optional["User"] = Relationship(back_populates="workspace_memberships")  # type: ignore[name-defined]
