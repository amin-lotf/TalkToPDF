from talk_to_pdf.backend.app.infrastructure.db.base import Base
from talk_to_pdf.backend.app.infrastructure.db.engine import engine

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
