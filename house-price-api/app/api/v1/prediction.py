from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.prediction import PredictionOut, PredictionRequest
from app.services import ml_service, prediction_service

router = APIRouter(prefix="/predictions", tags=["predictions"])
settings = get_settings()


def _payload_to_features(payload: PredictionRequest) -> list[float]:
    """Urutan HARUS sama dengan FEATURE_NAMES di trainer!"""
    return [
        payload.luas_tanah,
        payload.luas_bangunan,
        float(payload.jumlah_kamar),
        float(payload.jumlah_kamar_mandi),
        payload.skor_lokasi,
        float(payload.umur_bangunan),
    ]


@router.post("", response_model=PredictionOut, status_code=status.HTTP_201_CREATED)
def create_prediction(
    payload: PredictionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    harga = ml_service.predict_one(_payload_to_features(payload))
    if harga is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model belum siap. Jalankan: python -m app.ml.trainer",
        )

    return prediction_service.create_prediction(
        db,
        user_id=current_user.id,
        luas_tanah=payload.luas_tanah,
        luas_bangunan=payload.luas_bangunan,
        jumlah_kamar=payload.jumlah_kamar,
        jumlah_kamar_mandi=payload.jumlah_kamar_mandi,
        skor_lokasi=payload.skor_lokasi,
        umur_bangunan=payload.umur_bangunan,
        harga_prediksi=harga,
        model_version=settings.MODEL_VERSION,
    )


@router.get("", response_model=list[PredictionOut])
def list_predictions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return prediction_service.list_user_predictions(db, current_user.id, page, size)


@router.delete("/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prediction(
    prediction_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    record = prediction_service.get_owned_prediction(db, prediction_id, current_user.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediksi tidak ditemukan",
        )
    db.delete(record)
    db.commit()
