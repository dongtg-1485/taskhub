from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WorkspaceMemberRole
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository, Page
from app.schemas.workspace import CreateWorkspaceRequest, InviteMemberRequest


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def create(  # type: ignore[override]
        self,
        session: AsyncSession,
        *,
        owner_id: UUID,
        workspace_in: CreateWorkspaceRequest,
    ) -> Workspace:
        """
        Tạo mới workspace với owner_id và dữ liệu từ WorkspaceCreate.
        Override BaseRepository.create() để nhận tham số có tên rõ ràng thay vì dict.
        """
        data = workspace_in.model_dump()
        data["owner_id"] = owner_id
        return await super().create(session, data)

    async def get_by_id_for_user(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Workspace | None:
        """
        Lấy workspace theo ID, chỉ nếu user là thành viên (bất kể role).
        Dùng JOIN với bảng workspace_members để kiểm tra membership.
        Trả về None nếu workspace không tồn tại hoặc user không phải thành viên.
        """
        result = await session.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                Workspace.id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalars().first()

    async def list_by_owner(
        self,
        session: AsyncSession,
        owner_id: UUID,
        *,
        page: int = 0,
        limit: int = 20,
    ) -> Page[Workspace]:
        """
        Lấy danh sách workspace mà user là chủ sở hữu (owner).
        Dùng cho trang "My Workspaces" hiển thị workspace do user tạo.
        Sắp xếp theo created_at giảm dần: workspace mới nhất hiển thị trước.
        """
        offset = page * limit
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
        page: int = 0,
        limit: int = 20,
    ) -> Page[Workspace]:
        """
        Lấy tất cả workspace mà user là thành viên (bất kể role).
        Dùng JOIN với bảng workspace_members để lọc theo user_id.
        Khác list_by_owner(): bao gồm cả workspace user được mời vào, không chỉ workspace do họ tạo.
        """
        offset = page * limit
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
        return await super().create(session, data)

    async def add_members_bulk(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        members: list[InviteMemberRequest],
    ) -> list[WorkspaceMember]:
        """
        Thêm nhiều user vào workspace, bỏ qua những user đã là thành viên.
        """
        # Lấy danh sách user_id đã tồn tại trong workspace
        result = await session.execute(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id.in_([member.user_id for member in members]),
            )
        )
        existing_ids = set(result.scalars().all())

        # Chỉ thêm những user chưa là thành viên
        new_members = [
            member for member in members if member.user_id not in existing_ids
        ]
        if not new_members:
            return []

        members = [
            WorkspaceMember(
                workspace_id=workspace_id, user_id=member.user_id, role=member.role
            )
            for member in new_members
        ]
        session.add_all(members)
        await session.flush()
        for member in members:
            await session.refresh(member)
        return members

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
        page: int = 0,
        limit: int = 50,
    ) -> Page[WorkspaceMember]:
        """
        Lấy danh sách thành viên của một workspace.
        limit mặc định là 50 (cao hơn các list khác) vì workspace thường có ít thành viên
        và người dùng muốn xem toàn bộ danh sách mà không cần phân trang nhiều.
        """
        offset = page * limit
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
