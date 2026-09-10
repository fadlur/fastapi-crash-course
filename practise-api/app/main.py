from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import get_settings

settings = get_settings()

# Buat instance aplikasi FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
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
        "version": settings.APP_VERSION,
        "health": f"{settings.API_V1_PREFIX}/health",
    }