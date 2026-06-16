import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col


class Comment(SQLModel, table=True):
    """
    ORM model ánh xạ tới bảng 'comments'.
    Comment là bình luận của user trên một task cụ thể.
    Comment không thể sửa sau khi tạo (không có updated_at).
    """

    __tablename__ = "comments"

    # id: UUID primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # task_id: Comment thuộc về task nào
    # - nullable=False: Comment phải gắn với một task cụ thể
    # - ondelete="CASCADE": Xóa toàn bộ comment khi task bị xóa
    task_id: uuid.UUID = Field(
        foreign_key="tasks.id", nullable=False, ondelete="CASCADE"
    )

    # author_id: User đã viết comment, dùng cho audit trail
    # - nullable=False: Comment phải có tác giả
    # - Không có ondelete: Mặc định là RESTRICT, không cho xóa user nếu họ còn comment
    author_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    # content: Nội dung bình luận, không giới hạn độ dài (TEXT trong PostgreSQL)
    content: str

    # created_at: Thời điểm tạo comment
    # Chỉ có created_at, không có updated_at vì comment không được phép chỉnh sửa
    created_at: Optional[datetime] = Field(default=None, sa_column=created_at_col())

    task: Optional["Task"] = Relationship(back_populates="comments")  # type: ignore[name-defined]
    author: Optional["User"] = Relationship(back_populates="comments")  # type: ignore[name-defined]
