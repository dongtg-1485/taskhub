from datetime import datetime, timezone
from typing import Any, Union
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User, UserCreate, UserUpdate, UserRole
from app.repositories.base import BaseRepository, Page
from app.core.security import get_password_hash


class UserRepository(BaseRepository[User]):
    model = User

    async def create_user(self, session: AsyncSession, user_create: UserCreate) -> User:
        """
        Tạo một user mới.
        Caller chịu trách nhiệm validate dữ liệu trước khi truyền vào.
        """
        role = UserRole.ADMIN if user_create.is_superuser else UserRole.MEMBER
        data = user_create.model_dump(exclude={"password"})
        data["hashed_password"] = get_password_hash(user_create.password)
        data["role"] = role
        return await self.create(session, data)
    
    async def update_user(self, session: AsyncSession, db_user: User, user_in: Union[UserUpdate, dict[str, Any]]) -> User:
        """
        Cập nhật thông tin user.
        Caller chịu trách nhiệm validate dữ liệu trước khi truyền vào.
        """
        data = user_in if isinstance(user_in, dict) else user_in.model_dump(exclude_unset=True)
        if "password" in data:
            data["hashed_password"] = get_password_hash(data.pop("password"))
        if "is_superuser" in data:
            data["role"] = UserRole.ADMIN if data["is_superuser"] else UserRole.MEMBER
        return await self.update(session, db_user, data)
    
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """
        Tìm user theo địa chỉ email.
        Dùng chủ yếu trong luồng login để xác thực credentials.
        Email được index trong DB nên query này rất nhanh.
        """
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()
    
    # repositories/user.py — thêm method mới
    async def get_existing_ids(self, session: AsyncSession, ids: list[UUID]) -> set[UUID]:
        result = await session.execute(
            select(User.id).where(User.id.in_(ids))
        )
        return set(result.scalars().all())

    async def list(
        self,
        session: AsyncSession,
        *,
        page: int = 0,
        limit: int = 20,
    ) -> Page[User]:
        """
        Override base list() để thêm sắp xếp theo created_at giảm dần.
        User mới nhất hiển thị trước trong danh sách quản trị.
        """
        from sqlalchemy import func

        offset = page * limit
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
        """
        Tìm refresh token theo hash.
        Dùng khi client gửi refresh token lên để xin access token mới.
        token_hash được index (unique=True) nên query này rất nhanh.
        """
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalars().first()

    async def revoke(
        self, session: AsyncSession, token: RefreshToken
    ) -> RefreshToken:
        """
        Thu hồi một refresh token cụ thể bằng cách set revoked_at.
        Dùng soft-delete thay vì xóa để giữ audit trail và phát hiện token reuse.
        """
        return await self.update(
            session, token, {"revoked_at": datetime.now(timezone.utc)}
        )

    async def revoke_all_for_user(
        self, session: AsyncSession, user_id: UUID
    ) -> None:
        """
        Thu hồi tất cả refresh token còn hiệu lực của một user.
        Dùng khi user đổi mật khẩu hoặc yêu cầu đăng xuất khỏi tất cả thiết bị.
        Dùng bulk UPDATE thay vì update từng token để tối ưu hiệu suất.
        """
        now = datetime.now(timezone.utc)
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),  # type: ignore[union-attr]  # Chỉ revoke token chưa bị revoke
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
        """
        Tạo một refresh token record mới.
        Caller chịu trách nhiệm tính expires_at và hash raw token trước khi truyền vào.
        """
        data: dict[str, Any] = {
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
        }
        return await self.create(session, data)
