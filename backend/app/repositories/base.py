import math
from dataclasses import dataclass, field
from typing import Any, ClassVar, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


@dataclass
class Page(Generic[ModelT]):
    items: list[ModelT]
    total: int
    page: int
    limit: int
    pages: int = field(init=False)

    def __post_init__(self) -> None:
        self.pages = math.ceil(self.total / self.limit) if self.limit else 0

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class BaseRepository(Generic[ModelT]):
    model: ClassVar[type[Any]]  # type: ignore[misc]

    async def get(self, session: AsyncSession, id: UUID) -> ModelT | None:
        return await session.get(self.model, id)

    async def create(self, session: AsyncSession, data: dict[str, Any]) -> ModelT:
        db_obj = self.model(**data)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def update(
        self, session: AsyncSession, db_obj: ModelT, data: dict[str, Any]
    ) -> ModelT:
        for key, value in data.items():
            setattr(db_obj, key, value)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, db_obj: ModelT) -> None:
        await session.delete(db_obj)
        await session.flush()

    async def list(
        self, session: AsyncSession, *, page: int = 1, limit: int = 20
    ) -> "Page[ModelT]":
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
