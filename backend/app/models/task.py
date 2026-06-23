import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import created_at_col, updated_at_col
from app.models.enums import TaskPriority, TaskStatus


class TaskLabel(SQLModel, table=True):
    """
    Bảng trung gian (junction table) cho quan hệ many-to-many giữa Task và Label.
    Mỗi record đại diện cho một label được gán vào một task cụ thể.
    Composite primary key (task_id, label_id) đảm bảo mỗi label chỉ được gán một lần vào một task.
    """

    __tablename__ = "task_labels"

    # task_id: FK + khóa chính thứ nhất của composite PK
    # - ondelete="CASCADE": Xóa liên kết này khi task bị xóa, tránh orphan records
    task_id: uuid.UUID = Field(
        foreign_key="tasks.id", primary_key=True, ondelete="CASCADE"
    )

    # label_id: FK + khóa chính thứ hai của composite PK
    # - ondelete="CASCADE": Xóa liên kết này khi label bị xóa, tránh orphan records
    label_id: uuid.UUID = Field(
        foreign_key="labels.id", primary_key=True, ondelete="CASCADE"
    )


class Label(SQLModel, table=True):
    """
    Label (nhãn) dùng để phân loại và tìm kiếm task.
    Label được định nghĩa ở cấp project, các task trong project có thể dùng label đó.
    """

    __tablename__ = "labels"

    # __table_args__: Metadata cấp bảng, định nghĩa các constraint không khai báo được ở field
    # UniqueConstraint("project_id", "name"): Tên label phải duy nhất trong một project
    # (hai project khác nhau có thể có label cùng tên, nhưng không thể trùng trong cùng project)
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_labels_project_name"),
    )

    # id: UUID primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # project_id: Label thuộc về một project cụ thể
    # - nullable=False: Label phải gắn với một project
    # - ondelete="CASCADE": Xóa label khi project bị xóa
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE"
    )

    # name: Tên label, giới hạn 100 ký tự
    # (ngắn hơn 255 vì label thường là từ khóa ngắn như "bug", "feature", "urgent")
    name: str = Field(max_length=100)

    # color: Màu hiển thị của label dạng hex string (ví dụ: "#FF5733")
    # - max_length=7: Đúng bằng độ dài chuỗi "#RRGGBB" (1 ký tự '#' + 6 ký tự hex)
    color: str = Field(max_length=7)

    project: Optional["Project"] = Relationship(back_populates="labels")  # type: ignore[name-defined]

    # tasks: Danh sách task đang dùng label này
    # - link_model=TaskLabel: Chỉ định bảng trung gian cho quan hệ many-to-many
    tasks: list["Task"] = Relationship(back_populates="labels", link_model=TaskLabel)


class Task(SQLModel, table=True):
    """
    ORM model ánh xạ tới bảng 'tasks'.
    Task là đơn vị công việc nhỏ nhất, nằm trong một project.
    """

    __tablename__ = "tasks"

    # id: UUID primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # project_id: Task thuộc về project nào
    # - nullable=False: Task phải thuộc một project, không tồn tại độc lập
    # - ondelete="CASCADE": Xóa task khi project bị xóa
    project_id: uuid.UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE"
    )

    # assignee_id: User được giao thực hiện task
    # - default=None: Task có thể chưa được giao cho ai (unassigned)
    # - ondelete="SET NULL": Khi user bị xóa, task không bị xóa theo mà chỉ set
    #   assignee_id = NULL, giữ lại lịch sử task
    assignee_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )

    # created_by: User đã tạo task, dùng cho audit trail
    # - nullable=False: Task phải có người tạo
    # - Không có ondelete: Mặc định là RESTRICT, DB không cho xóa user nếu họ còn task
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    # title: Tiêu đề task, giới hạn 500 ký tự
    # (dài hơn 255 vì tiêu đề task có thể là một câu mô tả ngắn)
    title: str = Field(max_length=500)

    # description: Mô tả chi tiết task, không giới hạn độ dài (TEXT trong PostgreSQL)
    description: str | None = Field(default=None)

    # status: Trạng thái task trong workflow
    # - default=TaskStatus.TODO: Task mới mặc định là chưa bắt đầu
    status: TaskStatus = Field(default=TaskStatus.TODO)

    # priority: Mức độ ưu tiên của task
    # - default=TaskPriority.MEDIUM: Mặc định là ưu tiên trung bình
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)

    # due_date: Ngày đến hạn của task
    # - sa_type=Date(): Ánh xạ tới kiểu DATE (không phải TIMESTAMP) trong PostgreSQL,
    #   vì deadline thường tính theo ngày, không cần giờ phút
    # - default=None: Task có thể không có deadline
    due_date: date | None = Field(
        default=None,
        sa_type=Date(),  # type: ignore[call-arg]
    )

    # created_at / updated_at: Timestamp tự động quản lý bởi DB
    created_at: datetime | None = Field(default=None, sa_column=created_at_col())
    updated_at: datetime | None = Field(default=None, sa_column=updated_at_col())

    project: Optional["Project"] = Relationship(back_populates="tasks")  # type: ignore[name-defined]

    # labels: Danh sách label được gán vào task này
    # - link_model=TaskLabel: Chỉ định bảng trung gian cho quan hệ many-to-many
    labels: list[Label] = Relationship(back_populates="tasks", link_model=TaskLabel)

    # comments: Bình luận trên task
    # - cascade_delete=True: Xóa toàn bộ comment khi task bị xóa
    comments: list["Comment"] = Relationship(  # type: ignore[name-defined]
        back_populates="task", cascade_delete=True
    )
