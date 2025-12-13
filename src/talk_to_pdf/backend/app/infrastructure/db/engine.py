from sqlalchemy.ext.asyncio import create_async_engine
from talk_to_pdf.backend.app.core import settings

ASYNC_DATABASE_URI = settings.SQLALCHEMY_DATABASE_URL

engine = create_async_engine(
    ASYNC_DATABASE_URI,
    echo=False,
    pool_pre_ping=True,
    future=True,
)
