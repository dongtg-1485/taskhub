from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.repositories.base import BaseRepository, Page


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def list_by_task(
        self,
        session: AsyncSession,
        task_id: UUID,
        *,
        page: int = 1,
        limit: int = 50,
    ) -> Page[Comment]:
        """
        Lấy danh sách comment của một task.

        - Sắp xếp theo created_at tăng dần (ASC): comment cũ nhất hiển thị trước,
          giống cách hiển thị conversation trong chat (chronological order)
        - limit mặc định là 50 (cao hơn các list khác) vì comment thường được xem theo
          thread và người dùng muốn thấy nhiều comment hơn trong một lần load
        """
        offset = (page - 1) * limit
        total: int = (
            await session.execute(
                select(func.count())
                .select_from(Comment)
                .where(Comment.task_id == task_id)
            )
        ).scalar_one()
        result = await session.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc())  # ASC để hiển thị theo thứ tự thời gian
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)
