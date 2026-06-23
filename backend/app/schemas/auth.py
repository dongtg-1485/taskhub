"""Pydantic schema cho luồng xác thực (login / refresh / logout)."""

from sqlmodel import SQLModel


class TokenResponse(SQLModel):
    """Response trả về khi login / refresh thành công: gồm cả access và refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(SQLModel):
    """Request body cho /auth/refresh và /auth/logout: client gửi raw refresh token."""

    refresh_token: str
