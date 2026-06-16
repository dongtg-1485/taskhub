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
        """
        Lấy danh sách workspace mà user là chủ sở hữu (owner).
        Dùng cho trang "My Workspaces" hiển thị workspace do user tạo.
        Sắp xếp theo created_at giảm dần: workspace mới nhất hiển thị trước.
        """
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
        """
        Lấy tất cả workspace mà user là thành viên (bất kể role).
        Dùng JOIN với bảng workspace_members để lọc theo user_id.
        Khác list_by_owner(): bao gồm cả workspace user được mời vào, không chỉ workspace do họ tạo.
        """
        offset = (page - 1) * limit
        # base_q tái sử dụng cho cả COUNT và SELECT để tránh lặp điều kiện WHERE/JOIN
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
        """
        Lấy membership record của một user trong một workspace cụ thể.
        Dùng để kiểm tra quyền truy cập (user có phải thành viên không, role của họ là gì).
        Trả về None nếu user không phải thành viên của workspace đó.
        """
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
        """
        Thêm user vào workspace với role được chỉ định.
        Caller nên kiểm tra xem user đã là thành viên chưa trước khi gọi hàm này
        để tránh IntegrityError (composite PK constraint).
        """
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
        """Thay đổi role của một thành viên trong workspace."""
        return await self.update(session, member, {"role": role})

    async def list_members(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        *,
        page: int = 1,
        limit: int = 50,
    ) -> Page[WorkspaceMember]:
        """
        Lấy danh sách thành viên của một workspace.
        limit mặc định là 50 (cao hơn các list khác) vì workspace thường có ít thành viên
        và người dùng muốn xem toàn bộ danh sách mà không cần phân trang nhiều.
        """
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
