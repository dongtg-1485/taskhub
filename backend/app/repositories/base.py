import math
from dataclasses import dataclass, field
from typing import Any, ClassVar, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


@dataclass
class Page(Generic[ModelT]):
    """
    Container kết quả phân trang (pagination).
    Generic[ModelT] để type-safe với bất kỳ model nào.
    """

    items: list[ModelT]         # Danh sách record trong trang hiện tại
    total: int                  # Tổng số record thỏa điều kiện (dùng cho UI hiển thị "X results")
    page: int                   # Số trang hiện tại, bắt đầu từ 1
    limit: int                  # Số record tối đa mỗi trang
    pages: int = field(init=False)  # Tổng số trang, tự tính trong __post_init__ (không nhận qua init)

    def __post_init__(self) -> None:
        # Ceiling division: trang cuối có thể không đầy nhưng vẫn được tính là một trang
        self.pages = math.ceil(self.total / self.limit) if self.limit else 0

    @property
    def has_next(self) -> bool:
        """True nếu còn trang tiếp theo (dùng cho "Next" button ở UI)."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """True nếu có trang trước (dùng cho "Previous" button ở UI)."""
        return self.page > 1


class BaseRepository(Generic[ModelT]):
    """
    Repository cơ sở cung cấp các thao tác CRUD chung cho mọi model.

    Thiết kế:
    - Subclass khai báo class variable 'model' để chỉ định model tương ứng
    - Tất cả method dùng flush() thay vì commit() để các thao tác nằm trong một transaction
      duy nhất được quản lý bởi get_async_session() (Unit of Work pattern)
    - refresh() sau flush() để load lại các giá trị do DB tự sinh (server_default, sequences...)
    """

    # Subclass phải gán model class ở đây, ví dụ: model = User
    model: ClassVar[type[Any]]  # type: ignore[misc]

    async def get(self, session: AsyncSession, id: UUID) -> ModelT | None:
        """
        Lấy một record theo primary key.
        session.get() dùng identity map (cache trong session) trước khi query DB,
        hiệu quả hơn select() khi cùng object đã được load trong request.
        Trả về None nếu không tìm thấy.
        """
        return await session.get(self.model, id)

    async def create(self, session: AsyncSession, data: dict[str, Any]) -> ModelT:
        """
        Tạo mới một record.
        flush() ghi SQL INSERT vào DB trong transaction hiện tại nhưng chưa commit,
        refresh() load lại object để lấy các giá trị do DB tự sinh (id, created_at...).
        """
        db_obj = self.model(**data)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def update(
        self, session: AsyncSession, db_obj: ModelT, data: dict[str, Any]
    ) -> ModelT:
        """
        Cập nhật một record với các giá trị mới.
        Dùng setattr để cập nhật từng field, SQLAlchemy tự track thay đổi và sinh UPDATE.
        """
        for key, value in data.items():
            setattr(db_obj, key, value)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, db_obj: ModelT) -> None:
        """
        Xóa một record.
        flush() áp dụng SQL DELETE trong transaction hiện tại nhưng chưa commit,
        cho phép rollback nếu có lỗi ở bước sau trong cùng request.
        """
        await session.delete(db_obj)
        await session.flush()

    async def list(
        self, session: AsyncSession, *, page: int = 1, limit: int = 20
    ) -> "Page[ModelT]":
        """
        Lấy danh sách record có phân trang.
        Chạy hai query riêng biệt: một COUNT để lấy tổng, một SELECT để lấy dữ liệu trang hiện tại.
        Subclass nên override để thêm điều kiện WHERE hoặc thứ tự sắp xếp cụ thể.
        """
        offset = (page - 1) * limit
        total: int = (
            await session.execute(
                select(func.count()).select_from(self.model)
            )
        ).scalar_one()
        result = await session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)
