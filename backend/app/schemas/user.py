import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.enums import UserRole
from app.models.user import UserBase


class RegisterUserRequest(SQLModel):
    """Schema dùng khi user tự đăng ký."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class CreateUserRequest(UserBase):
    """Schema dùng khi admin tạo user mới, kế thừa đầy đủ từ UserBase."""

    password: str = Field(min_length=8, max_length=128)


class UpdateUserRequest(UserBase):
    """Schema dùng khi admin cập nhật thông tin user, tất cả field đều optional."""

    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UpdateCurrentUserRequest(SQLModel):
    """Schema dùng khi user tự cập nhật thông tin của mình (không cho đổi role/active)."""

    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePasswordRequest(SQLModel):
    """Schema dùng khi user đổi password, yêu cầu xác nhận password hiện tại."""

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(UserBase):
    """Schema trả về cho client, không bao gồm hashed_password và các field nhạy cảm."""

    id: uuid.UUID
    role: UserRole
    created_at: datetime | None = None


class UsersResponse(SQLModel):
    """Schema trả về danh sách user có kèm tổng số (dùng cho phân trang)."""

    data: list[UserResponse]
    count: int
