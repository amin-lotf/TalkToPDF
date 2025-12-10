from sqlalchemy.ext.asyncio import create_async_engine
from talk_to_pdf.backend.app.core import settings

def _to_async_sqlite_dsn(dsn: str) -> str:
    """
    If user provided a sync SQLite DSN (e.g., 'sqlite:///app.db'),
    convert it to the async driver DSN ('sqlite+aiosqlite:///app.db').
    Otherwise, return as-is.
    """
    if dsn.startswith("sqlite:///") or dsn.startswith("sqlite:///:"):
        return "sqlite+aiosqlite" + dsn[len("sqlite"):]
    if dsn.startswith("sqlite://"):
        # rare forms; still convert
        return "sqlite+aiosqlite" + dsn[len("sqlite"):]
    return dsn

ASYNC_DATABASE_URI = _to_async_sqlite_dsn(settings.SQLALCHEMY_DATABASE_URL)


engine = create_async_engine(
    ASYNC_DATABASE_URI,
    echo=False,                # turn True if you want verbose SQL logs
    pool_pre_ping=True,        # keep connections healthy
    future=True,
)