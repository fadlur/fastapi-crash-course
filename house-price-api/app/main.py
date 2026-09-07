import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (daftarkan tabel ke Base.metadata)
from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.services import ml_service

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Buat tabel (DEV). Di produksi gunakan migrasi (Alembic).
    Base.metadata.create_all(bind=engine)
    # 2. Muat model ML SEKALI saat startup, bukan tiap request.
    ml_service.load_model()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: mengizinkan frontend lain (web/mobile) memanggil API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan semua route di bawah /api/v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    return {
        "nama": settings.APP_NAME,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
