import uuid
from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import UserRole


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.MEMBER)
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())
    updated_at: Optional[datetime] = Field(default=None, sa_column=updated_at_col())

    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user", cascade_delete=True
    )
    owned_workspaces: list["Workspace"] = Relationship(back_populates="owner")
    workspace_memberships: list["WorkspaceMember"] = Relationship(back_populates="user")
    comments: list["Comment"] = Relationship(back_populates="author")


class UserPublic(UserBase):
    id: uuid.UUID
    role: UserRole
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    token_hash: str = Field(unique=True)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore[call-arg]
    revoked_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)  # type: ignore[call-arg]
    )
    created_at: datetime = Field(sa_column=created_at_col())

    user: User | None = Relationship(back_populates="refresh_tokens")
