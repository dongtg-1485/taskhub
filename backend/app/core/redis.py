import redis.asyncio as aioredis

from app.core.config import settings

# Connection pool dùng chung toàn bộ ứng dụng, tránh tạo connection mới cho mỗi request.
# max_connections=20: giới hạn số connection đồng thời tới Redis.
# decode_responses=True: tự decode bytes → str, không cần gọi .decode() thủ công.
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)


def get_redis() -> aioredis.Redis:
    """
    Trả về Redis client sử dụng connection pool chung.

    Dùng làm FastAPI dependency — mỗi request dùng chung pool, không tạo connection mới.
    """
    return aioredis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """Đóng toàn bộ connection trong pool — gọi khi ứng dụng shutdown."""
    await redis_pool.aclose()


async def invalidate_by_pattern(redis: aioredis.Redis, pattern: str) -> None:
    """
    Xóa toàn bộ cache key khớp pattern glob.

    Dùng cho cache invalidation sau các thao tác write (tạo, cập nhật, xóa).
    """
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
