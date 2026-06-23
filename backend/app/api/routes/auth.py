from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api.deps import AsyncSessionDep, CurrentUser
from app.core import security
from app.core.config import settings
from app.core.security import (
    create_refresh_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.models._schemas import Message, NewPassword
from app.models.user import User
from app.repositories import refresh_tokens, users
from app.schemas.auth import RefreshTokenRequest, TokenResponse
from app.schemas.user import RegisterUserRequest, UserResponse
from app.utils import verify_password_reset_token

router = APIRouter(prefix="/auth", tags=["auth"])


async def _authenticate(
    session: AsyncSession, email: str, password: str
) -> User | None:
    """
    Xác thực user theo email + password (phiên bản async dùng repository).

    Chống timing attack: vẫn chạy verify_password với một hash giả khi không tìm thấy
    user, để thời gian phản hồi không tiết lộ email có tồn tại hay không.
    Tự upgrade hash bcrypt -> argon2 nếu verify_password trả về hash mới.
    """
    user = await users.get_by_email(session, email)
    if not user:
        verify_password(password, crud.DUMMY_HASH)
        return None
    verified, updated_hash = verify_password(password, user.hashed_password)
    if not verified:
        return None
    if updated_hash:
        await users.update(session, user, {"hashed_password": updated_hash})
    return user


async def _issue_token_pair(session: AsyncSession, user: User) -> TokenResponse:
    """
    Cấp một cặp token mới cho user và lưu hash của refresh token vào DB.

    - access_token: JWT ngắn hạn, verify offline, không lưu DB
    - refresh_token: opaque token dài hạn, chỉ lưu SHA-256 hash để có thể revoke
    """
    access_token = security.create_access_token(
        user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    raw_refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
    )
    await refresh_tokens.create_token(
        session,
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=expires_at,
    )
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Email already registered"}},
)
async def register(
    *, session: AsyncSessionDep, user_in: RegisterUserRequest
) -> UserResponse:
    """
    Register a new user account.

    - **email**: unique, used as login identifier
    - **password**: minimum 8 characters, stored as Argon2 hash
    - **full_name**: optional display name
    """
    existing = await users.get_by_email(session, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await users.create(
        session,
        {
            "email": user_in.email,
            "full_name": user_in.full_name,
            "hashed_password": get_password_hash(user_in.password),
        },
    )
    return user  # type: ignore[return-value]


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={400: {"description": "Incorrect email or password / inactive user"}},
)
async def login(
    *,
    session: AsyncSessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """
    Authenticate with email + password, returns an access + refresh token pair.

    Dùng OAuth2 password form (`username` = email) để tương thích nút Authorize của Swagger.
    """
    user = await _authenticate(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return await _issue_token_pair(session, user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: {"description": "Invalid, expired or revoked refresh token"}},
)
async def refresh(
    *, session: AsyncSessionDep, body: RefreshTokenRequest
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    Áp dụng **refresh token rotation**: token cũ bị revoke ngay khi dùng, client phải
    lưu refresh token mới trả về. Nếu một token đã dùng bị gửi lại -> bị từ chối, giúp
    phát hiện token bị đánh cắp (token reuse).
    """
    db_token = await refresh_tokens.get_by_hash(
        session, hash_refresh_token(body.refresh_token)
    )
    if db_token is None or db_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if db_token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )
    user = await users.get(session, db_token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    # Rotation: thu hồi token vừa dùng rồi cấp cặp token mới
    await refresh_tokens.revoke(session, db_token)
    return await _issue_token_pair(session, user)


@router.post(
    "/reset-password",
    response_model=Message,
    responses={400: {"description": "Invalid token or inactive user"}},
)
async def reset_password(*, session: AsyncSessionDep, body: NewPassword) -> Message:
    """
    Đặt lại mật khẩu bằng token nhận qua email.

    Token được tạo từ endpoint quên mật khẩu (chưa triển khai). Lỗi trả về giống nhau
    dù token sai hay user không tồn tại, để không tiết lộ email nào đã đăng ký.
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )
    user = await users.get_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    await users.update(
        session, user, {"hashed_password": get_password_hash(body.new_password)}
    )
    return Message(message="Password updated successfully")


@router.post("/test-token", response_model=UserResponse)
def test_token(current_user: CurrentUser) -> UserResponse:
    """
    Kiểm tra access token hiện tại, trả về thông tin user đang đăng nhập.
    """
    return current_user  # type: ignore[return-value]


@router.post("/logout", response_model=Message)
async def logout(*, session: AsyncSessionDep, body: RefreshTokenRequest) -> Message:
    """
    Log out by revoking the given refresh token.

    Idempotent: luôn trả về success kể cả khi token không tồn tại hoặc đã bị revoke,
    để không tiết lộ token nào hợp lệ.
    """
    db_token = await refresh_tokens.get_by_hash(
        session, hash_refresh_token(body.refresh_token)
    )
    if db_token is not None and db_token.revoked_at is None:
        await refresh_tokens.revoke(session, db_token)
    return Message(message="Successfully logged out")
