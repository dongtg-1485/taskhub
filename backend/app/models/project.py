import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import ProjectStatus


class Project(SQLModel, table=True):
    """
    ORM model ánh xạ tới bảng 'projects'.
    Project là đơn vị quản lý công việc, chứa các task và label.
    """

    __tablename__ = "projects"

    # id: UUID primary key, Python tự sinh khi tạo object
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # workspace_id: FK tới workspace chứa project này
    # - nullable=False: Project phải thuộc một workspace, không tồn tại độc lập
    # - ondelete="CASCADE": Tự động xóa project ở DB level khi workspace bị xóa
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False, ondelete="CASCADE"
    )

    # name: Tên project, giới hạn 255 ký tự
    name: str = Field(max_length=255)

    # description: Mô tả chi tiết project
    # - default=None: Không bắt buộc, project có thể không có mô tả
    # - Không giới hạn max_length vì ánh xạ tới TEXT trong PostgreSQL
    description: str | None = Field(default=None)

    # status: Trạng thái vòng đời của project
    # - default=ProjectStatus.ACTIVE: Project mới mặc định là đang hoạt động
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)

    # created_at / updated_at: Timestamp tự động quản lý bởi DB
    created_at: datetime | None = Field(default=None, sa_column=created_at_col())
    updated_at: datetime | None = Field(default=None, sa_column=updated_at_col())

    workspace: Optional["Workspace"] = Relationship(back_populates="projects")  # type: ignore[name-defined]

    # tasks: Danh sách task trong project
    # - cascade_delete=True: Khi xóa project, xóa luôn tất cả task bên trong
    tasks: list["Task"] = Relationship(back_populates="project", cascade_delete=True)  # type: ignore[name-defined]

    # labels: Danh sách label được định nghĩa trong project
    # - cascade_delete=True: Khi xóa project, xóa luôn tất cả label
    labels: list["Label"] = Relationship(back_populates="project", cascade_delete=True)  # type: ignore[name-defined]
