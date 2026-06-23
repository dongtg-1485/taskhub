from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task, TaskLabel
from app.repositories.base import BaseRepository, Page


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def list_by_project(
        self,
        session: AsyncSession,
        project_id: UUID,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        page: int = 0,
        limit: int = 20,
    ) -> Page[Task]:
        """
        Lấy danh sách task trong một project với nhiều bộ lọc tùy chọn.

        Các filter đều optional, có thể kết hợp:
        - status: Lọc theo trạng thái (TODO, IN_PROGRESS, IN_REVIEW, DONE)
        - priority: Lọc theo mức ưu tiên (LOW, MEDIUM, HIGH, URGENT)
        - assignee_id: Lọc task được giao cho một user cụ thể
        Sắp xếp theo created_at giảm dần: task mới nhất hiển thị trước.
        """
        offset = page * limit
        base_where = [Task.project_id == project_id]

        if status is not None:
            base_where.append(Task.status == status)
        if priority is not None:
            base_where.append(Task.priority == priority)
        if assignee_id is not None:
            base_where.append(Task.assignee_id == assignee_id)

        total: int = (
            await session.execute(
                select(func.count()).select_from(Task).where(*base_where)
            )
        ).scalar_one()
        result = await session.execute(
            select(Task)
            .where(*base_where)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)

    async def add_label(
        self, session: AsyncSession, task_id: UUID, label_id: UUID
    ) -> None:
        """
        Gán một label vào task.
        Kiểm tra trùng lặp trước khi insert để tránh IntegrityError từ composite PK constraint.
        Dùng idempotent approach: không báo lỗi nếu label đã được gán rồi.
        """
        existing = await session.execute(
            select(TaskLabel).where(
                TaskLabel.task_id == task_id,
                TaskLabel.label_id == label_id,
            )
        )
        if existing.scalars().first() is None:
            session.add(TaskLabel(task_id=task_id, label_id=label_id))
            await session.flush()

    async def remove_label(
        self, session: AsyncSession, task_id: UUID, label_id: UUID
    ) -> None:
        """
        Bỏ một label khỏi task.
        Dùng DELETE trực tiếp vào bảng trung gian task_labels thay vì thao tác qua ORM relationship
        để tránh phải load toàn bộ danh sách label của task vào memory.
        """
        await session.execute(
            delete(TaskLabel).where(
                TaskLabel.task_id == task_id,
                TaskLabel.label_id == label_id,
            )
        )
        await session.flush()
