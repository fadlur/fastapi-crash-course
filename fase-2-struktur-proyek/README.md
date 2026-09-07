# Fase 2 — Struktur Proyek Profesional 🏗️

**Tujuan fase ini:**

- Membangun kerangka project `house-price-api` yang terstruktur & siap tumbuh.
- Paham _layering_ (route → logic → data) ala FastAPI yang benar.
- Paham konfigurasi dengan `pydantic-settings`, `.env`, CORS, dan lifespan.

> Ini "jembatan" dari contoh kecil di Fase 1 menuju aplikasi sungguhan.
> **Kenapa struktur penting?** Project tesis yang cuma 1 file `main.py` akan jadi
> mimpi buruk saat sudah 1000+ baris dan harus di-deploy. Struktur yang rapi = mudah
> ditest, mudah didebug, mudah dideploy.

---

## 1. Konsep: Layering di FastAPI

Bayangkan seperti organisasi restoran:

```
HTTP request
   │
   ▼
┌───────────────────────┐
│  API layer (routers)  │  ← tahu "URL apa", "terima data apa"
│  = pelayan            │
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│ Service layer         │  ← berisi logika bisnis (panggil model ML, hitung, dll)
│ = koki               │
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│ Data layer (models)   │  ← bicara ke database
│ = gudang             │
└───────────────────────┘
```

Aturan emasnya: **router jangan diisi logika panjang**. Router itu tipis — dia hanya
menerima request, memanggil service, lalu mengembalikan response. Ini yang bikin kode
mudah ditest & dirawat.

---

## 2. Struktur folder project kita

Buat struktur ini di dalam `house-price-api/` (kamu sudah ada di sana dari Fase 0):

```
house-price-api/
├── app/                      ← paket utama aplikasi
│   ├── __init__.py           ← (file kosong, penanda folder = Python package)
│   ├── main.py               ← titik masuk: bikin FastAPI app
│   ├── core/                 ← konfigurasi & hal lintas-modul
│   │   ├── __init__.py
│   │   └── config.py
│   └── api/                  ← layer route
│       ├── __init__.py
│       └── v1/               ← versi API (v1). Kalau API berubah besar → v2
│           ├── __init__.py
│           ├── api.py        ← gabungkan semua router
│           └── health.py     ← endpoint /health
├── requirements.txt
├── .env.example
├── .gitignore
```

> Buat semua file `__init__.py` dalam keadaan **kosong**. Fungsinya cuma memberi tahu
> Python bahwa folder ini adalah _package_ yang bisa di-import.
>
> Jalankan perintah pembuat folder (bisa lewat terminal atau klik kanan di VS Code):
>
> ```bash
> mkdir -p app/core app/api/v1
> touch app/__init__.py app/core/__init__.py app/api/__init__.py app/api/v1/__init__.py
> ```

---

## 3. Install semua dependency project

Buat file **`requirements.txt`**:

```txt
# ===== Web framework =====
fastapi>=0.115
uvicorn[standard]>=0.30

# ===== Data & validasi =====
pydantic>=2.7
pydantic-settings>=2.2
email-validator>=2.1

# ===== Database =====
sqlalchemy>=2.0.30
psycopg[binary]>=3.2

# ===== Auth =====
PyJWT>=2.8
bcrypt>=4.1
python-multipart>=0.0.9

# ===== Machine Learning =====
numpy>=1.26
scikit-learn>=1.4
joblib>=1.3

# ===== Testing =====
pytest>=8.0
httpx>=0.27
```

Install:

```bash
pip install -r requirements.txt
```

> Kita install semua sekarang walau belum dipakai semua — supaya kamu tidak berhenti
> di tengah jalan gara-gara package kurang. (Nanti di Fase 7 kita bahas memisahkan
> package "development" vs "production".)

---

## 4. Konfigurasi: `pydantic-settings` + file `.env`

### Kenapa butuh ini?

Kamu pasti tidak mau menaruh password database / secret key **di dalam kode** — karena
kode itu di-commit ke Git. Solusinya: simpan nilai rahasia & konfigurasi di file
**`.env`**, lalu baca dari kode.

Urutan prioritas nilai konfigurasi (paling kuat di atas):

```
1. Environment variable (dari Docker / VPS)
2. File .env
3. Nilai default di dalam kode
```

### Buat `app/core/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Semua konfigurasi aplikasi dalam satu tempat."""

    model_config = SettingsConfigDict(
        env_file=".env",       # baca nilai dari file .env
        env_file_encoding="utf-8",
        extra="ignore",        # abaikan variable lain di environment
    )

    # ----- Aplikasi -----
    APP_NAME: str = "House Price Prediction API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ----- CORS -----
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ----- Database (dipakai di Fase 3) -----
    DATABASE_URL: str = "sqlite+pysqlite:///./house_price.db"

    # ----- Auth (dipakai di Fase 4) -----
    SECRET_KEY: str = "ganti-ini-sebelum-produksi"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ----- Model ML (dipakai di Fase 5) -----
    MODEL_PATH: str = "app/ml/artifacts/model.joblib"
    MODEL_VERSION: str = "v1.0.0"


@lru_cache
def get_settings() -> Settings:
    """Dipanggil berkali-kali tapi hasilnya di-cache (dibaca 1x saja)."""
    return Settings()
```

**Penjelasan konsep:**

- `BaseSettings` dari `pydantic-settings` = seperti `BaseModel` Pydantic, tapi otomatis
  membaca dari file `.env` dan environment.
- Setiap atribut (`APP_NAME`, `SECRET_KEY`, ...) otomatis cocok dengan variable
  ber-nama sama di `.env`.
- `@lru_cache` → `get_settings()` hanya membaca file `.env` **sekali** lalu di-cache.
  Efisien & jadi pola umum FastAPI.

### Buat `.env.example` (template yang boleh di-commit):

```bash
# ===== Environment =====
APP_ENV=development
DEBUG=true

# ===== Database =====
# Untuk jalan lokal: Postgres berjalan di Docker (lihat Fase 3)
DATABASE_URL=postgresql+psycopg://app:app_password@localhost:5432/house_price
# Quickstart tanpa Postgres? Ganti baris di atas jadi:
# DATABASE_URL=sqlite+pysqlite:///./house_price.db

# ===== Auth =====
SECRET_KEY=dev-only-secret-ganti-di-produksi
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ===== Model ML =====
MODEL_PATH=app/ml/artifacts/model.joblib
MODEL_VERSION=v1.0.0

# ===== CORS =====
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

Lalu salin jadi `.env` (file ini **jangan** di-commit, isinya rahasia):

```bash
cp .env.example .env
```

### Buat `.gitignore`:

```gitignore
# Python
__pycache__/
*.pyc
.venv/

# Environment (rahasia!)
.env

# Model ML (bisa di-generate ulang oleh trainer)
app/ml/artifacts/*.joblib

# Testing
.pytest_cache/
.coverage

# OS
.DS_Store
```

> 🧠 Kenapa `.env` di-gitignore tapi `.env.example` tidak? Karena `.env` berisi rahasia
> asli (password, secret key), sedangkan `.env.example` hanya contoh — orang lain bisa
> menyalinnya jadi `.env` sendiri. Ini praktik standar produksi.

---

## 5. Endpoint `/health`

Healthcheck adalah "cek jantung" aplikasi — dipakai Docker (Fase 7) & monitoring untuk
tahu apakah aplikasi hidup.

Buat **`app/api/v1/health.py`**:

```python
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])
settings = get_settings()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "app_env": settings.APP_ENV,
    }
```

---

## 6. Router aggregator: `app/api/v1/api.py`

Semua router versi v1 digabung di sini, supaya `main.py` tetap bersih.

```python
from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
```

> Setiap kali menambah modul route baru (auth, prediction), kita cukup menambah satu
> baris `api_router.include_router(...)` di sini.

---

## 7. Titik masuk: `app/main.py`

```python
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
        "health": f"{settings.API_V1_PREFIX}/health",
    }
```

**Penjelasan:**

- `app.include_router(api_router, prefix="/api/v1")` → semua route di `api_router`
  otomatis ber-prefix `/api/v1`. Jadi `/health` menjadi `/api/v1/health`.
- `include_in_schema=False` di `/` → endpoint ini tidak muncul di `/docs` (hanya
  halaman sapaan).
- Middleware CORS = mengizinkan browser dari origin lain (misal frontend React di
  port 3000) memanggil API. Tanpa ini, browser akan memblokir request.

> 🧠 Kenapa pakai prefix `/api/v1`? Kalau suatu saat kamu ubah API secara besar-besaran
> (misal format response berubah), kamu bisa buat `/api/v2` tanpa merusak client lama
> yang masih pakai v1. Di tesis, ini juga nilai plus saat presentasi.

---

## 8. Cek hasil fase ini ✅

Jalankan dari folder `house-price-api`:

```bash
uvicorn app.main:app --reload
```

1. Buka `http://127.0.0.1:8000/` → halaman sapaan dengan nama aplikasi.
2. Buka `http://127.0.0.1:8000/docs` → sekarang hanya ada endpoint `/health`.
3. Buka `http://127.0.0.1:8000/api/v1/health` → dapat:
   ```json
   { "status": "ok", "app_env": "development" }
   ```

> 💡 Karena dijalankan dengan `uvicorn app.main:app` (bukan `main:app`), `app` sekarang
> adalah _package_. Ini alasan kenapa path file berubah jadi `app.main`.

---

## 9. Yang kamu pelajari di fase ini

- Struktur layering: **api → (service) → data**, router yang tipis.
- `pydantic-settings`: config terpusat + `.env` untuk rahasia.
- CORS & cara mengizinkan frontend lain.
- Prefix `/api/v1` dan router aggregator.

---

## 🎯 Latihan

1. Tambahkan `APP_VERSION` di `Settings` dan tampilkan di endpoint `/`.
2. Coba matikan `--reload`, jalankan ulang `uvicorn app.main:app`, ubah kode, dan
   lihat bahwa perubahan **tidak** otomatis ke-load (ini membuktikan kenapa di
   produksi kita build ulang container, bukan pakai `--reload`).

> Sudah rapi strukturnya? Lanjut ke **[Fase 3 — Database](../fase-3-database/README.md)** 👈
> Saatnya nyambungin PostgreSQL + SQLAlchemy.
