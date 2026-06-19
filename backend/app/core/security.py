import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# Cấu hình password hasher với hai thuật toán theo thứ tự ưu tiên:
# 1. Argon2Hasher: Thuật toán hiện đại, được OWASP khuyên dùng (memory-hard, resistant với GPU attack)
# 2. BcryptHasher: Fallback để verify các hash cũ (nếu migrate từ hệ thống cũ dùng bcrypt)
# pwdlib dùng Argon2 khi hash mới, tự nhận dạng bcrypt khi verify hash cũ.
# verify_and_update() sẽ tự động rehash bcrypt -> argon2 và trả về hash mới để lưu lại
password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)

# Thuật toán ký JWT: HMAC-SHA256
# Dùng symmetric key (SECRET_KEY) nên phù hợp cho monolith; đổi sang RS256 nếu cần microservice
ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    """
    Tạo JWT access token.

    - subject: Thường là user ID, encode vào claim 'sub' theo chuẩn JWT (RFC 7519)
    - expires_delta: Thời gian hiệu lực; dùng timezone.utc để nhất quán giữa các server
    - Ký bằng SECRET_KEY + HS256, token có thể verify mà không cần truy vấn DB
    """
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    """
    Xác minh password và tự động upgrade hash nếu cần.

    Trả về tuple (is_valid, new_hash):
    - is_valid: True nếu plain_password khớp với hashed_password
    - new_hash: Hash Argon2 mới nếu hash cũ dùng bcrypt và cần upgrade, None nếu không cần
    Caller nên lưu new_hash vào DB nếu không phải None để hoàn tất quá trình upgrade.
    """
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password bằng Argon2 (thuật toán đứng đầu trong PasswordHash)."""
    return password_hash.hash(password)


def create_refresh_token() -> str:
    """
    Sinh raw refresh token: chuỗi ngẫu nhiên 48 byte (~64 ký tự URL-safe).

    Khác với access token (là JWT self-contained), refresh token là 'opaque token':
    server không nhúng thông tin gì vào đó, chỉ tra cứu trong DB. Nhờ vậy mới có thể
    revoke được (JWT không revoke được vì verify offline). Token có entropy rất cao
    nên không thể brute-force.
    """
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    """
    Hash refresh token bằng SHA-256 trước khi lưu/tra cứu trong DB.

    Lý do dùng SHA-256 (nhanh) thay vì Argon2 (chậm) như password:
    - Refresh token là chuỗi ngẫu nhiên entropy cao, không thể brute-force như password
      do người dùng tự đặt, nên không cần hàm hash chậm (memory-hard).
    - SHA-256 cho kết quả deterministic -> tra cứu bằng index trên cột token_hash (O(log n)).
      Argon2 có salt ngẫu nhiên mỗi lần hash nên không thể lookup bằng so khớp trực tiếp.
    Mục đích hash: nếu DB bị lộ, attacker không lấy được raw token để dùng.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()
