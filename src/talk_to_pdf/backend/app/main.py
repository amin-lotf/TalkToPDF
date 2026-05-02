from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from talk_to_pdf.backend.app.api.v1.router import api_router
from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.exception_handlers import register_exception_handlers
from talk_to_pdf.backend.app.infrastructure.db.init_db import init_db


def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db()
        yield

    app = FastAPI(lifespan=lifespan)
    if settings.CORS_ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(api_router,prefix="/api/v1")
    @app.get("/health")
    def health():
        return {"status": "ok"}

    register_exception_handlers(app)
    return app

app = create_app()
