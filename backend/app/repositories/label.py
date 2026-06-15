from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Label
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    model = Label

    async def list_by_project(
        self, session: AsyncSession, project_id: UUID
    ) -> list[Label]:
        result = await session.execute(
            select(Label)
            .where(Label.project_id == project_id)
            .order_by(Label.name)
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, session: AsyncSession, project_id: UUID, name: str
    ) -> Label | None:
        result = await session.execute(
            select(Label).where(
                Label.project_id == project_id,
                Label.name == name,
            )
        )
        return result.scalars().first()
