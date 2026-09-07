import logging
from pathlib import Path

import joblib
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_model = None  # disimpan di memori setelah load


def load_model() -> bool:
    """Muat model.joblib dari disk → memori. Panggil sekali saat startup."""
    global _model

    path = Path(settings.MODEL_PATH)
    if not path.exists():
        logger.warning("File model tidak ditemukan: %s. Jalankan trainer dulu.", path)
        _model = None
        return False

    _model = joblib.load(path)
    logger.info("Model ML %s berhasil dimuat (%s)", settings.MODEL_VERSION, path)
    return True


def is_ready() -> bool:
    """Apakah model sudah siap dipakai?"""
    return _model is not None


def predict_one(features: list[float]) -> float | None:
    """Prediksi 1 baris fitur. Urutan fitur HARUS sama dengan training."""
    if _model is None:
        return None
    result = _model.predict(np.asarray([features], dtype=float))
    return float(result[0])
