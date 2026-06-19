from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate

# Engine đồng bộ (sync) dùng cho các API route cũ (legacy) chưa được chuyển sang async
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

# Engine bất đồng bộ (async) dùng cho các route mới theo repository pattern
# - echo=False: Không in SQL queries ra log (đặt True khi debug để xem câu query thực tế)
# - pool_pre_ping=True: Trước mỗi lần lấy connection từ pool, kiểm tra kết nối còn sống không.
#   Nếu DB bị khởi động lại hoặc connection timeout, engine sẽ tự kết nối lại thay vì lỗi
async_engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,
    pool_pre_ping=True,
)

# Session factory cho async engine
# - class_=AsyncSession: Dùng AsyncSession (non-blocking) thay vì Session thông thường
# - expire_on_commit=False: Sau khi commit, object vẫn giữ nguyên giá trị attribute trong bộ nhớ.
#   Nếu để True (mặc định), mọi attribute sẽ bị "expire" sau commit và phải query lại DB
#   khi access, điều này gây lỗi trong async context (lazy load không hoạt động với async)
# - autocommit=False: Transaction phải được commit thủ công, tránh commit ngoài ý muốn
# - autoflush=False: Không tự flush (ghi vào DB trong transaction) trước mỗi query,
#   giúp kiểm soát thứ tự flush và tránh partial write không mong muốn
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency cung cấp AsyncSession cho mỗi request.

    Hoạt động theo pattern Unit of Work:
    - Tự động commit khi toàn bộ request handler hoàn thành thành công
    - Tự động rollback toàn bộ transaction khi có exception, đảm bảo tính nhất quán dữ liệu
    - Context manager đảm bảo session luôn được đóng sau khi request kết thúc (dù thành công hay lỗi)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def init_db(session: Session) -> None:
    """
    Khởi tạo dữ liệu mặc định khi ứng dụng start lần đầu.

    Tạo superuser đầu tiên nếu chưa tồn tại trong DB.
    Hàm này idempotent: an toàn khi gọi nhiều lần (không tạo trùng).
    """
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
