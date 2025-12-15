from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from talk_to_pdf.backend.app.infrastructure.db.engine import engine

# Async session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)