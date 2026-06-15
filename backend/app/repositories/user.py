from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User
from app.repositories.base import BaseRepository, Page


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def list(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        limit: int = 20,
    ) -> Page[User]:
        from sqlalchemy import func

        offset = (page - 1) * limit
        total: int = (
            await session.execute(select(func.count()).select_from(User))
        ).scalar_one()
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())
        return Page(items=items, total=total, page=page, limit=limit)


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(
        self, session: AsyncSession, token_hash: str
    ) -> RefreshToken | None:
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalars().first()

    async def revoke(
        self, session: AsyncSession, token: RefreshToken
    ) -> RefreshToken:
        return await self.update(
            session, token, {"revoked_at": datetime.now(timezone.utc)}
        )

    async def revoke_all_for_user(
        self, session: AsyncSession, user_id: UUID
    ) -> None:
        now = datetime.now(timezone.utc)
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),  # type: ignore[union-attr]
            )
            .values(revoked_at=now)
        )
        await session.flush()

    async def create_token(
        self,
        session: AsyncSession,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        data: dict[str, Any] = {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
        }
        return await self.create(session, data)
