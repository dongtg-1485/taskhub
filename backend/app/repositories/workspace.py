from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WorkspaceMemberRole
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository, Page


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def list_by_owner(
        self,
        session: AsyncSession,
        owner_id: UUID,
        *,
        page: int = 1,
        limit: int = 20,
    ) -> Page[Workspace]:
        offset = (page - 1) * limit
        total: int = (
            await session.execute(
                select(func.count())
                .select_from(Workspace)
                .where(Workspace.owner_id == owner_id)
            )
        ).scalar_one()
        result = await session.execute(
            select(Workspace)
            .where(Workspace.owner_id == owner_id)
            .order_by(Workspace.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)

    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        *,
        page: int = 1,
        limit: int = 20,
    ) -> Page[Workspace]:
        offset = (page - 1) * limit
        base_q = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        total: int = (
            await session.execute(
                select(func.count())
                .select_from(Workspace)
                .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                .where(WorkspaceMember.user_id == user_id)
            )
        ).scalar_one()
        result = await session.execute(
            base_q.order_by(Workspace.created_at.desc()).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember

    async def get_member(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalars().first()

    async def add_member(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceMemberRole,
    ) -> WorkspaceMember:
        data: dict[str, Any] = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": role,
        }
        return await self.create(session, data)

    async def update_role(
        self,
        session: AsyncSession,
        member: WorkspaceMember,
        role: WorkspaceMemberRole,
    ) -> WorkspaceMember:
        return await self.update(session, member, {"role": role})

    async def list_members(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        *,
        page: int = 1,
        limit: int = 50,
    ) -> Page[WorkspaceMember]:
        offset = (page - 1) * limit
        total: int = (
            await session.execute(
                select(func.count())
                .select_from(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace_id)
            )
        ).scalar_one()
        result = await session.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)
