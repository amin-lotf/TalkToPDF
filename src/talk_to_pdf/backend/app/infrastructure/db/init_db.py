from sqlalchemy import text

from talk_to_pdf.backend.app.infrastructure.db.base import Base
from talk_to_pdf.backend.app.infrastructure.db.engine import engine, ASYNC_DATABASE_URI


async def init_db() -> None:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # If SQLite, enable WAL for better concurrent readers/writers
        if ASYNC_DATABASE_URI.startswith("sqlite+aiosqlite://"):
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))