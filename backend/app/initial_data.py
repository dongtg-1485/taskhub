import asyncio
import logging

from app.core.db import AsyncSessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init() -> None:
    async with AsyncSessionLocal() as session:
        await init_db(session)
        await session.commit()


def main() -> None:
    logger.info("Creating initial data")
    asyncio.run(init())
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
