from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])
settings = get_settings()

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "app_env": settings.APP_ENV
    }