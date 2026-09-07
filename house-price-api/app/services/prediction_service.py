from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prediction import Prediction


def create_prediction(
    db: Session,
    *,
    user_id: int,
    luas_tanah: float,
    luas_bangunan: float,
    jumlah_kamar: int,
    jumlah_kamar_mandi: int,
    skor_lokasi: float,
    umur_bangunan: int,
    harga_prediksi: float,
    model_version: str,
) -> Prediction:
    record = Prediction(
        user_id=user_id,
        luas_tanah=luas_tanah,
        luas_bangunan=luas_bangunan,
        jumlah_kamar=jumlah_kamar,
        jumlah_kamar_mandi=jumlah_kamar_mandi,
        skor_lokasi=skor_lokasi,
        umur_bangunan=umur_bangunan,
        harga_prediksi=harga_prediksi,
        model_version=model_version,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_user_predictions(db: Session, user_id: int, page: int, size: int):
    stmt = (
        select(Prediction)
        .where(Prediction.user_id == user_id)
        .order_by(Prediction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(stmt).all())


def get_owned_prediction(db: Session, prediction_id: int, user_id: int):
    return db.scalar(
        select(Prediction).where(
            Prediction.id == prediction_id,
            Prediction.user_id == user_id,
        )
    )
