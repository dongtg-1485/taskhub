import uuid
from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import UserRole


class UserBase(SQLModel):
    """Schema dùng chung cho các Pydantic schema liên quan đến User (không phải table)."""

    # unique=True: Mỗi email chỉ được đăng ký một tài khoản
    # index=True: Tạo DB index để tăng tốc query lookup theo email (dùng nhiều khi login)
    # max_length=255: Giới hạn theo RFC 5321, đủ cho mọi địa chỉ email hợp lệ
    email: EmailStr = Field(unique=True, index=True, max_length=255)

    # is_active: Cho phép vô hiệu hóa tài khoản mà không cần xóa khỏi DB
    is_active: bool = True

    # is_superuser: Flag đặc biệt cho superuser, bypass mọi permission check
    is_superuser: bool = False

    # full_name: Không bắt buộc, user có thể không điền khi đăng ký
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    """Schema dùng khi admin tạo user mới, kế thừa đầy đủ từ UserBase."""

    # min_length=8: Đảm bảo password đủ mạnh tối thiểu
    # max_length=128: Ngăn chặn tấn công DoS bằng cách gửi password cực dài
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    """Schema dùng khi user tự đăng ký, chỉ bao gồm các field cần thiết."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
    """Schema dùng khi admin cập nhật thông tin user, tất cả field đều optional."""

    # type: ignore vì override kiểu của UserBase (từ required thành optional)
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    """Schema dùng khi user tự cập nhật thông tin của mình (không cho đổi role/active)."""

    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    """Schema dùng khi user đổi password, yêu cầu xác nhận password hiện tại."""

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    """
    ORM model ánh xạ tới bảng 'users' trong PostgreSQL.
    table=True: Đánh dấu đây là SQLModel table (không chỉ là Pydantic schema).
    """

    __tablename__ = "users"

    # id: Khóa chính UUID
    # - default_factory=uuid.uuid4: Python tự sinh UUID mới mỗi khi tạo object,
    #   không phụ thuộc vào DB để tránh round-trip thêm
    # - primary_key=True: Khai báo khóa chính của bảng
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # hashed_password: Chỉ lưu hash, không bao giờ lưu plain text password vì lý do bảo mật
    hashed_password: str

    # role: Vai trò người dùng trong hệ thống
    # - default=UserRole.MEMBER: Người dùng mới mặc định là MEMBER, không có đặc quyền
    role: UserRole = Field(default=UserRole.MEMBER)

    # created_at: Thời điểm tạo record
    # - default=None: Python không set giá trị; DB tự set qua server_default trong created_at_col()
    # - sa_column=created_at_col(): Dùng column factory từ base.py để tái sử dụng cấu hình
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())

    # updated_at: Thời điểm cập nhật gần nhất
    # - sa_column=updated_at_col(): Có thêm onupdate=func.now() để tự cập nhật khi UPDATE
    updated_at: Optional[datetime] = Field(default=None, sa_column=updated_at_col())

    # refresh_tokens: Danh sách refresh token của user
    # - cascade_delete=True: Khi xóa user, tất cả refresh token liên quan cũng bị xóa tự động
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user", cascade_delete=True
    )

    # owned_workspaces: Danh sách workspace mà user là chủ sở hữu
    owned_workspaces: list["Workspace"] = Relationship(back_populates="owner")

    # workspace_memberships: Danh sách tư cách thành viên của user trong các workspace
    workspace_memberships: list["WorkspaceMember"] = Relationship(back_populates="user")

    # comments: Danh sách bình luận mà user đã tạo
    comments: list["Comment"] = Relationship(back_populates="author")


class UserPublic(UserBase):
    """Schema trả về cho client, không bao gồm hashed_password và các field nhạy cảm."""

    id: uuid.UUID
    role: UserRole
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    """Schema trả về danh sách user có kèm tổng số (dùng cho phân trang)."""

    data: list[UserPublic]
    count: int


class RefreshToken(SQLModel, table=True):
    """
    Lưu trữ refresh token để hỗ trợ cơ chế đăng nhập lâu dài và logout an toàn.
    Chỉ lưu hash của token, không bao giờ lưu raw token.
    """

    __tablename__ = "refresh_tokens"

    # id: UUID primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # user_id: Khóa ngoại tham chiếu tới bảng users
    # - nullable=False: Token phải thuộc về một user cụ thể
    # - ondelete="CASCADE": Khi user bị xóa, tất cả token của họ cũng bị xóa ở DB level
    #   (cascade ở DB level là backup cho cascade_delete=True ở ORM level)
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )

    # token_hash: Hash của raw refresh token (dùng SHA-256 hoặc tương đương)
    # - unique=True: Mỗi hash là duy nhất, tránh collision và trùng lặp token
    token_hash: str = Field(unique=True)

    # expires_at: Thời điểm hết hạn của token
    # - sa_type=DateTime(timezone=True): Dùng TIMESTAMPTZ để so sánh thời gian chính xác
    #   khi server chạy ở nhiều timezone khác nhau
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore[call-arg]

    # revoked_at: Thời điểm token bị thu hồi (NULL nếu token vẫn còn hiệu lực)
    # - default=None: NULL có nghĩa là token chưa bị revoke
    # - Dùng soft-delete thay vì xóa record để giữ audit trail
    revoked_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)  # type: ignore[call-arg]
    )

    # created_at: Thời điểm token được tạo, dùng để audit và debug
    created_at: datetime = Field(sa_column=created_at_col())

    user: User | None = Relationship(back_populates="refresh_tokens")
