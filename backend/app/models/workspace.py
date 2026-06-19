import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import WorkspaceMemberRole


def _utcnow() -> datetime:
    """Trả về thời điểm hiện tại ở UTC, dùng làm default_factory cho các timestamp field."""
    return datetime.now(timezone.utc)


class Workspace(SQLModel, table=True):
    """
    ORM model ánh xạ tới bảng 'workspaces'.
    Workspace là đơn vị tổ chức cao nhất, chứa nhiều project.
    """

    __tablename__ = "workspaces"

    # id: UUID primary key, Python tự sinh khi tạo object
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # name: Tên workspace, giới hạn 255 ký tự để đảm bảo không vượt quá VARCHAR(255) trong DB
    name: str = Field(max_length=255)

    # owner_id: Khóa ngoại tham chiếu tới user sở hữu workspace
    # - nullable=False: Workspace phải có chủ sở hữu
    # - Không có ondelete="CASCADE": Không tự động xóa workspace khi user bị xóa,
    #   vì cần transfer ownership hoặc xử lý thủ công trước khi xóa user
    owner_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    # created_at / updated_at: Dùng server-side default qua column factory
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())
    updated_at: Optional[datetime] = Field(default=None, sa_column=updated_at_col())

    owner: Optional["User"] = Relationship(back_populates="owned_workspaces")  # type: ignore[name-defined]

    # members: Danh sách thành viên workspace (thông qua bảng workspace_members)
    # - cascade_delete=True: Khi xóa workspace, xóa luôn tất cả membership records
    members: list["WorkspaceMember"] = Relationship(
        back_populates="workspace", cascade_delete=True
    )

    # projects: Danh sách project trong workspace
    # - cascade_delete=True: Khi xóa workspace, xóa luôn tất cả project bên trong
    projects: list["Project"] = Relationship(  # type: ignore[name-defined]
        back_populates="workspace", cascade_delete=True
    )


class WorkspaceMember(SQLModel, table=True):
    """
    Bảng liên kết (association table) giữa Workspace và User, thể hiện tư cách thành viên.
    Composite primary key (workspace_id, user_id) đảm bảo mỗi user chỉ có một membership
    trong mỗi workspace.
    """

    __tablename__ = "workspace_members"

    # workspace_id: Khóa ngoại + khóa chính thứ nhất của composite PK
    # - primary_key=True: Là một phần của composite primary key
    # - ondelete="CASCADE": Tự động xóa membership ở DB level khi workspace bị xóa
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", primary_key=True, ondelete="CASCADE"
    )

    # user_id: Khóa ngoại + khóa chính thứ hai của composite PK
    # - primary_key=True: Là một phần của composite primary key
    # - ondelete="CASCADE": Tự động xóa membership ở DB level khi user bị xóa
    user_id: uuid.UUID = Field(
        foreign_key="users.id", primary_key=True, ondelete="CASCADE"
    )

    # role: Vai trò của thành viên trong workspace này
    # - default=WorkspaceMemberRole.VIEWER: Thành viên mới được thêm vào với quyền chỉ xem,
    #   admin workspace có thể nâng quyền sau
    role: WorkspaceMemberRole = Field(default=WorkspaceMemberRole.VIEWER)

    # joined_at: Thời điểm gia nhập workspace
    # - default_factory=_utcnow: Python set giá trị khi tạo object (không qua DB server_default)
    #   vì composite PK table không có sa_column dạng Column riêng biệt
    # - sa_type=DateTime(timezone=True): Đảm bảo lưu TIMESTAMPTZ trong PostgreSQL
    joined_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=DateTime(timezone=True),  # type: ignore[call-arg]
    )

    workspace: Optional[Workspace] = Relationship(back_populates="members")
    user: Optional["User"] = Relationship(back_populates="workspace_memberships")  # type: ignore[name-defined]
