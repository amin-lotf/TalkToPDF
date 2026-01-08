import asyncio
from pathlib import Path

import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    test_url = settings.TEST_SQLALCHEMY_DATABASE_URL

    engine = create_async_engine(test_url, pool_pre_ping=True)

    def run_migrations():
        cfg = Config("alembic.ini")
        sync_url = test_url.replace("+asyncpg", "")
        cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(cfg, "head")

    await asyncio.to_thread(run_migrations)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(db_engine) -> AsyncSession:
    async with db_engine.connect() as conn:
        # Outer transaction (never committed)
        await conn.begin()

        SessionLocal = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        session = SessionLocal()

        # Start a SAVEPOINT so app code can commit safely
        await session.begin_nested()

        # If the code under test commits, restart the SAVEPOINT automatically
        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(sess, trans):
            if trans.nested and not trans._parent.nested:
                sess.begin_nested()

        try:
            yield session
        finally:
            await session.close()
            # Rollback outer transaction → DB clean for next test
            await conn.rollback()


@pytest_asyncio.fixture
async def uow(session):
    return SqlAlchemyUnitOfWork(session)

@pytest_asyncio.fixture
def pdf_bytes() -> bytes:
    """
    Read a PDF file from disk and return its bytes.
    """
    pdf_path=Path("scripts/sample.pdf")
    return pdf_path.read_bytes()