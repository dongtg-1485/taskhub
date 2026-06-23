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
        """
        Lấy tất cả label trong một project, sắp xếp theo tên (alphabetical).
        Không phân trang vì số lượng label trong một project thường ít
        và cần hiển thị toàn bộ trong dropdown/filter UI.
        """
        result = await session.execute(
            select(Label).where(Label.project_id == project_id).order_by(Label.name)
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, session: AsyncSession, project_id: UUID, name: str
    ) -> Label | None:
        """
        Tìm label theo tên trong một project cụ thể.
        Dùng để kiểm tra tên label đã tồn tại chưa trước khi tạo mới,
        tránh trùng với unique constraint (project_id, name) trong DB.
        Trả về None nếu chưa có label với tên đó trong project.
        """
        result = await session.execute(
            select(Label).where(
                Label.project_id == project_id,
                Label.name == name,
            )
        )
        return result.scalars().first()
