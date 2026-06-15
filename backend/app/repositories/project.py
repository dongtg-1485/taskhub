from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.repositories.base import BaseRepository, Page


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def list_by_workspace(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        *,
        status: ProjectStatus | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> Page[Project]:
        offset = (page - 1) * limit
        base_where = [Project.workspace_id == workspace_id]
        if status is not None:
            base_where.append(Project.status == status)

        total: int = (
            await session.execute(
                select(func.count())
                .select_from(Project)
                .where(*base_where)
            )
        ).scalar_one()
        result = await session.execute(
            select(Project)
            .where(*base_where)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)
