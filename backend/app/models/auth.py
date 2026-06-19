"""Pydantic schema cho luồng xác thực (login / refresh / logout)."""
from sqlmodel import SQLModel


class TokenPair(SQLModel):
    """Response trả về khi login / refresh thành công: gồm cả access và refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(SQLModel):
    """Request body cho /auth/refresh và /auth/logout: client gửi raw refresh token."""

    refresh_token: str
