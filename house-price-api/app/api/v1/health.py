from fastapi import APIRouter

from app.core.config import get_settings
from app.services import ml_service

router = APIRouter(tags=["system"])
settings = get_settings()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "app_env": settings.APP_ENV,
        "model_ready": ml_service.is_ready(),
    }
