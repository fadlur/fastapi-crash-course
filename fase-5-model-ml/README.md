# Fase 5 — Integrasi Model ML 🤖 (paling mirip tesis kamu!)

**Tujuan fase ini:**

- Melatih model regresi dummy yang realistis (sklearn + joblib).
- Memuat model **sekali saat startup**, bukan tiap request.
- Membuat endpoint `/predictions` → prediksi → simpan ke database.
- Paham `sync vs async` saat memanggil kerja berat (CPU-bound) dari FastAPI.

> Ini bagian yang **paling mirip dengan tesis kamu**: punya `model.joblib`, lalu
> memanggilnya dari dalam API. Perhatikan baik-baik pola "muat sekali, pakai banyak" —
> ini sering jadi kesalahan pemula yang membuat API lemot.

---

## 1. Konsep: Jangan muat model di tiap request! 🚫

Banyak yang menulis `joblib.load("model.joblib")` **di dalam** endpoint. Itu salah:

```
❌ Per request → load file model (bisa 100-500ms!) → baru predict
✅ Saat startup → load 1x ke memori → tiap request tinggal predict (ms)

100 request = 100x load file  (lambat & boros RAM/IO)
100 request = 100x predict    (cepat, model sudah di memori)
```

Memuat file model (apalagi model besar seperti LSTM/CNN) itu operasi **I/O + deserialisasi
yang mahal**. Kita pindahkan ke **`lifespan`** (yang sudah kita bahas di Fase 3) — jalan
sekali saat server start.

### Bonus konsep: `sync` vs `async` endpoint

FastAPI punya dua jenis endpoint:

```python
@app.post("/predict")
def predict(...):          # SYNC  → dijalankan di threadpool, tidak memblokir
    ...model.predict...    #  model ML = CPU-bound → pakai SYNC

@app.get("/data")
async def get_data(...):   # ASYNC → untuk I/O (database, HTTP) yang menunggu
    ...await...
```

Model ML (predict) itu **CPU-bound** — sibuk menghitung, bukan menunggu. Kalau kita pakai
`async def` untuk predict, kita justru **memblokir event loop** dan melambatkan request
lain. Jadi: **endpoint yang manggil model ML sebaiknya `def` (sync)**, dan FastAPI
otomatis menjalankannya di _threadpool_ supaya request lain tetap jalan.

> 🧠 Ini pengetahuan produksi yang jarang dibahas di tutorial! Sebagian besar endpoint
> tesis (CRUD db, predict model) cukup pakai `def` biasa — FastAPI yang atur.

---

## 2. Latih model dummy kita

Buat folder `app/ml/` dengan file kosong `__init__.py`, lalu file **`app/ml/trainer.py`**:

```python
"""Latih model regresi sederhana → app/ml/artifacts/model.joblib."""
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

FEATURE_NAMES = [
    "luas_tanah",
    "luas_bangunan",
    "jumlah_kamar",
    "jumlah_kamar_mandi",
    "skor_lokasi",
    "umur_bangunan",
]


def generate_data(n: int = 3000, seed: int = 42):
    """Buat data sintetis mirip harga rumah. Ganti dengan data tesis kamu!"""
    rng = np.random.default_rng(seed)

    luas_tanah = rng.uniform(60, 600, n)
    luas_bangunan = luas_tanah * rng.uniform(0.4, 0.8, n)
    jumlah_kamar = rng.integers(1, 6, n)
    jumlah_kamar_mandi = rng.integers(1, 4, n)
    skor_lokasi = rng.uniform(0, 10, n)
    umur_bangunan = rng.integers(0, 40, n)

    X = np.column_stack(
        [luas_tanah, luas_bangunan, jumlah_kamar,
         jumlah_kamar_mandi, skor_lokasi, umur_bangunan]
    )

    # Rumus harga "tersembunyi" + noise biar mirip data asli
    noise = rng.normal(0, 5e7, n)
    y = (
        2.5e6 * luas_tanah
        + 3.0e6 * luas_bangunan
        + 8e7 * skor_lokasi
        - 1.2e6 * umur_bangunan
        + noise
    )
    y = np.maximum(y, 5e7)
    return X, y


def main():
    X, y = generate_data()
    model = LinearRegression()
    model.fit(X, y)

    out_dir = Path(__file__).parent / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "model.joblib"
    joblib.dump(model, out_path)

    print(f"Model tersimpan di: {out_path}")
    print(f"R² score: {model.score(X, y):.4f}")


if __name__ == "__main__":
    main()
```

Jalankan trainer:

```bash
python -m app.ml.trainer
```

Output:

```
Model tersimpan di: app/ml/artifacts/model.joblib
R² score: 0.99xx
```

> 🔁 **Untuk tesis kamu:** cukup ganti `generate_data()` dengan pipeline training asli
> kamu (load dataset, preprocessing, fit), dan pastikan hasilnya disimpan dengan
> `joblib.dump(model, ...)`. Konsep sisanya **identik**.

> ⚠️ **Ingat urutan fitur!** Model belajar dari urutan kolom tertentu
> (`luas_tanah, luas_bangunan, ...`). Saat prediksi nanti, urutannya **harus sama
> persis**. Di tesis, simpan daftar nama fitur bersama model — seperti `FEATURE_NAMES`
> di atas.

---

## 3. Service model: muat sekali, predict kapan saja

Buat folder `app/services/` dengan file kosong `__init__.py`, lalu file
**`app/services/ml_service.py`**:

```python
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
```

**Penjelasan:**

- `_model` disimpan sebagai **variabel global modul** (bukan per request).
- `predict_one` mengembalikan `None` kalau model belum di-load → endpoint bisa
  membalas 503 (biar client tahu "model belum siap", bukan error aneh).

---

## 4. Schema Pydantic untuk input & output prediksi

Buat **`app/schemas/prediction.py`**:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    """Input: fitur rumah yang dikirim client."""

    luas_tanah: float = Field(gt=0, description="Luas tanah (m²)")
    luas_bangunan: float = Field(gt=0, description="Luas bangunan (m²)")
    jumlah_kamar: int = Field(ge=1, le=20)
    jumlah_kamar_mandi: int = Field(ge=1, le=20)
    skor_lokasi: float = Field(ge=0, le=10, description="Skor lokasi 0-10")
    umur_bangunan: int = Field(ge=0, le=200, description="Umur bangunan (tahun)")


class PredictionOut(BaseModel):
    """Output: hasil prediksi (juga dipakai untuk riwayat)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    luas_tanah: float
    luas_bangunan: float
    jumlah_kamar: int
    jumlah_kamar_mandi: int
    skor_lokasi: float
    umur_bangunan: int
    harga_prediksi: float
    model_version: str
    created_at: datetime
```

---

## 5. Service bisnis: simpan & baca riwayat prediksi

Buat **`app/services/prediction_service.py`** — logika bisnis dipisah dari route
(ingat layering di Fase 2):

```python
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
```

---

## 6. Router prediksi

Buat **`app/api/v1/prediction.py`**:

```python
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
```

**Konsep penting yang tercermin di sini:**

- Endpoint `create_prediction` adalah **`def` (sync)** → tidak memblokir server saat
  model ML menghitung.
- Router tipis: dia cuma **memanggil service** (`ml_service.predict_one`, lalu
  `prediction_service.create_prediction`) — logika ada di service.
- Hanya pemilik data yang bisa lihat/hapus (`user_id == current_user.id`).

---

## 7. Update: muat model saat startup & daftarkan router

Update **`app/main.py`** — tambahkan `ml_service.load_model()` di dalam `lifespan`
(timpa seluruh isi):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.services import ml_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Buat tabel (DEV). Di produksi pakai migrasi (Fase 8).
    Base.metadata.create_all(bind=engine)
    # 2. Muat model ML SEKALI saat startup, bukan tiap request.
    ml_service.load_model()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    return {
        "nama": settings.APP_NAME,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
```

Update **`app/api/v1/api.py`** (timpa):

```python
from fastapi import APIRouter

from app.api.v1 import auth, health, prediction

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(prediction.router)
```

Update **`app/api/v1/health.py`** supaya menampilkan status model (timpa):

```python
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
```

> Perhatikan log di terminal saat start — harusnya ada baris:
> `Model ML v1.0.0 berhasil dimuat (...)`.

---

## 8. Cek hasil fase ini ✅

Jalankan `uvicorn app.main:app --reload` (pastikan sudah login via Authorize di `/docs`,
seperti Fase 4).

1. `GET /api/v1/health` → `{"status": "ok", ..., "model_ready": true}`.
2. `POST /api/v1/predictions` (login dulu!) dengan body:
   ```json
   {
     "luas_tanah": 120,
     "luas_bangunan": 90,
     "jumlah_kamar": 3,
     "jumlah_kamar_mandi": 2,
     "skor_lokasi": 8,
     "umur_bangunan": 10
   }
   ```
   → response 201 berisi `harga_prediksi` (jutaan rupiah) + data tersimpan.
3. `GET /api/v1/predictions` → daftar riwayat prediksi milikmu (pagination).
4. Kirim body tanpa login → 401. Kirim fitur aneh (`jumlah_kamar: 99`) → 422.
5. Cek database:
   ```bash
   docker compose exec db psql -U app -d house_price -c \
     'select id, user_id, harga_prediksi, model_version from predictions;'
   ```

> 🎉 Ini dia inti project: **input → model ML → hasil tersimpan di DB per user**.

---

## 9. Yang kamu pelajari di fase ini

- Memuat model **sekali di startup** vs per request.
- `def` (sync) untuk kerja CPU-bound model ML — FastAPI mengurus threadpool-nya.
- Pemisahan logika ke `services/` (ml_service & prediction_service).
- Urutan fitur harus konsisten training ↔ inference.
- Error 503 saat model belum siap.

---

## 🎯 Latihan

1. Matikan server, hapus `app/ml/artifacts/model.joblib`, start lagi, lalu panggil
   `/health` → `model_ready: false`, dan POST predictions → 503. Jalankan trainer,
   restart, dan lihat perbedaannya. Ini membuktikan pentingnya lifecycle model.
2. Tambahkan endpoint `GET /predictions/stats` yang menghitung `count` dan `avg`
   harga prediksi milik user yang login (pakai SQLAlchemy `func.count`, `func.avg`).

> Model ML sudah nyambung! Lanjut ke **[Fase 6 — Testing & Logging](../fase-6-testing-logging/README.md)** 👈
> Supaya project kamu teruji otomatis & gampang di-debug.
