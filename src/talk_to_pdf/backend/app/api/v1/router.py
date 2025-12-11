# app/interfaces/api/router.py
from fastapi import APIRouter

from talk_to_pdf.backend.app.api.v1.users import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router.router)
