from contextlib import asynccontextmanager
from fastapi import FastAPI
from talk_to_pdf.backend.app.infrastructure.db import init_db


def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db()
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok"}
    return app

app = create_app()