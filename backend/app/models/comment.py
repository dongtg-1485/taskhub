import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col


class Comment(SQLModel, table=True):
    __tablename__ = "comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    task_id: uuid.UUID = Field(
        foreign_key="tasks.id", nullable=False, ondelete="CASCADE"
    )
    author_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    content: str
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())

    task: Optional["Task"] = Relationship(back_populates="comments")  # type: ignore[name-defined]
    author: Optional["User"] = Relationship(back_populates="comments")  # type: ignore[name-defined]
