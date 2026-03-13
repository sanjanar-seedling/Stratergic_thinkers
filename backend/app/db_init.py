"""Database initialization and migrations.

Creates schema and tables.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import get_settings
from app.models import Base

logger = logging.getLogger(__name__)
settings = get_settings()


async def init_db():
    """Initialize database schema and tables."""
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )

    async with engine.begin() as conn:
        # Create schema
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.database_schema}"))
        logger.info(f"Schema '{settings.database_schema}' created or already exists")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created")

    await engine.dispose()


async def drop_db():
    """Drop all tables (use with caution!)."""
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All tables dropped")

    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        print("⚠️  WARNING: This will drop all tables!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            asyncio.run(drop_db())
            print("✅ Database dropped")
        else:
            print("❌ Cancelled")
    else:
        asyncio.run(init_db())
        print("✅ Database initialized")
