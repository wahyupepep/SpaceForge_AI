"""Run release migrations using the direct database URL and a deployment lock."""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


async def migrate() -> None:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    engine = create_async_engine(
        settings.database_url_unpooled or settings.database_url, poolclass=NullPool
    )

    def upgrade(connection) -> None:  # type: ignore[no-untyped-def]
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET lock_timeout = '60s'"))
            await connection.execute(text("SELECT pg_advisory_lock(1598334965)"))
            await connection.commit()
            try:
                await connection.run_sync(upgrade)
                await connection.commit()
            finally:
                await connection.rollback()
                await connection.execute(text("SELECT pg_advisory_unlock(1598334965)"))
                await connection.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
