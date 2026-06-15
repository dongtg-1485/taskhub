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
        page: int = 1,
        limit: int = 20,
    ) -> Page[Task]:
        offset = (page - 1) * limit
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
        await session.execute(
            delete(TaskLabel).where(
                TaskLabel.task_id == task_id,
                TaskLabel.label_id == label_id,
            )
        )
        await session.flush()
