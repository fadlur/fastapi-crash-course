# Fase 3 — Database: SQLAlchemy 2.0 + PostgreSQL 🗄️

**Tujuan fase ini:**

- Menjalankan PostgreSQL (via Docker) sebagai database lokal.
- Memahami SQLAlchemy 2.0: `engine`, `Session`, model ORM, dependency `get_db`.
- Membuat tabel `users` & `predictions` (persis pola tesis kamu).

> Ini fase di mana project mulai "hidup" dengan data. Kita pakai **SQLAlchemy 2.0**
> gaya baru (type annotation `Mapped[...]` + `mapped_column`) — bukan gaya lama
> `Column(...)`. Kalau tesis kamu masih gaya lama, sekarang saatnya upgrade ke gaya
> modern yang direkomendasikan.

---

## 1. Konsep: cara SQLAlchemy bicara ke PostgreSQL

SQLAlchemy punya 3 bagian utama:

| Bagian          | Perumpamaan       | Fungsi                                                 |
| --------------- | ----------------- | ------------------------------------------------------ |
| **Engine**      | Sambungan listrik | Menghubungkan Python ke database (1x dibuat)           |
| **Session**     | Telepon           | Transaksi: kirim perintah & terima hasil (per request) |
| **Model (ORM)** | Resep data        | Python class ↔ tabel database                          |

Alur per request di FastAPI nanti:

```
Request masuk
   → dependency get_db() membuat 1 Session
   → route pakai session utk query/simpan
   → session ditutup otomatis (finally)
```

> 🧠 **Kenapa 1 session per request?** Session itu "boros" & tidak aman dibagi antar
> thread. FastAPI menyelesaikannya dengan **dependency injection** (`get_db`) — tiap
> request dapat session baru yang bersih, lalu ditutup rapi.

---

## 2. Jalankan PostgreSQL dengan Docker

Buat file **`docker-compose.yml`** di root `house-price-api/`:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app_password
      POSTGRES_DB: house_price
    ports:
      - "5432:5432" # host : container
    volumes:
      - pgdata:/var/lib/postgresql/data # data tetap ada walau container restart
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d house_price"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
```

Jalankan (pastikan Docker Desktop sudah menyala):

```bash
docker compose up -d db
docker compose ps
```

Kamu akan lihat status `healthy`. Artinya PostgreSQL sudah jalan di `localhost:5432`
dengan user `app`, password `app_password`, database `house_price`.

> Kalau kamu belum mau pakai Docker sekarang, kamu bisa fallback ke SQLite dulu:
> ganti `DATABASE_URL` di `.env` menjadi
> `sqlite+pysqlite:///./house_price.db`. Semua kode di fase ini tetap jalan — bedanya
> hanya di "mesin" databasenya. (SQLite cocok utk dev, PostgreSQL utk produksi.)

---

## 3. Koneksi database: `app/core/database.py`

Buat file **`app/core/database.py`**:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite butuh argumen khusus untuk multi-thread; PostgreSQL tidak.
_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,   # cek koneksi dulu sebelum pakai (aman utk produksi)
)

# "Pabrik session": dipanggil utk membuat 1 session per request
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base untuk semua model ORM."""


def get_db():
    """Dependency FastAPI: 1 session DB per request, auto close."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Penjelasan konsep:**

- **`create_engine`** — dibuat **sekali** saat app start. Jangan dibuat per request!
- **`pool_pre_ping=True`** — sebelum tiap query, SQLAlchemy cek apakah koneksi masih
  hidup. Ini menyelamatkanmu dari error `server has gone away` saat database restart
  (sering terjadi di produksi!).
- **`get_db` adalah generator** (`yield`) → inilah bentuk _dependency_ FastAPI untuk
  database. `finally: db.close()` menjamin session selalu ditutup, bahkan kalau terjadi
  error di tengah request.

---

## 4. Model: tabel `users` & `predictions`

### Buat `app/models/__init__.py`:

```python
from app.models.prediction import Prediction
from app.models.user import User

__all__ = ["User", "Prediction"]
```

> File ini penting: mengimpor semua model di satu tempat, supaya `Base.metadata`
> "tahu" semua tabel yang harus dibuat. Kalau ada model baru, daftarkan di sini.

### Buat `app/models/user.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))  # diisi Fase 4
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relasi: 1 user punya banyak predictions
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
```

### Buat `app/models/prediction.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # ---- Fitur input (dikirim client) ----
    luas_tanah: Mapped[float] = mapped_column(Float)
    luas_bangunan: Mapped[float] = mapped_column(Float)
    jumlah_kamar: Mapped[int] = mapped_column(Integer)
    jumlah_kamar_mandi: Mapped[int] = mapped_column(Integer)
    skor_lokasi: Mapped[float] = mapped_column(Float)
    umur_bangunan: Mapped[int] = mapped_column(Integer)

    # ---- Hasil prediksi (dari model ML, Fase 5) ----
    harga_prediksi: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="predictions")
```

**Penjelasan konsep SQLAlchemy 2.0:**

- `Mapped[float]` → tipe Python di sisi ORM; `mapped_column(Float)` → tipe di DB.
- `ForeignKey("users.id")` → kolom `user_id` merujuk tabel `users` (relasi).
- `ondelete="CASCADE"` → kalau user dihapus, prediction-nya ikut terhapus.
- `relationship(...)` → mempermudah akses relasi di Python (`user.predictions`).
- `index=True` pada kolom yang sering dipakai di `WHERE` → query lebih cepat.

> 🧠 Ini persis pola tabel tesis kamu: **satu tabel "master" (user) dan satu tabel
> "hasil/riwayat" yang melekat ke user**. Model ML kamu tinggal "diselipkan" sebagai
> kolom hasil seperti `harga_prediksi`.

---

## 5. Aktifkan pembuatan tabel saat startup

Update **`app/main.py`** (timpa seluruh isi):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (daftarkan tabel ke Base.metadata)
from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.database import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DEV: buat tabel otomatis.
    # PRODUKSI: gunakan migrasi (Alembic), dibahas di Fase 8.
    Base.metadata.create_all(bind=engine)
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
        "version": settings.APP_VERSION,
        "health": f"{settings.API_V1_PREFIX}/health",
    }
```

**Penjelasan konsep `lifespan`:**

- `lifespan` = kode yang jalan **sekali saat app start** (sebelum `yield`) dan **sekali
  saat app mati** (setelah `yield`).
- Ini tempat yang tepat untuk: buat tabel, muat model ML (Fase 5), buka koneksi, dll.
- Di produksi kamu mengganti `create_all` dengan **Alembic migration** — karena
  `create_all` tidak bisa mengubah tabel yang sudah ada (misal menambah kolom baru).

---

## 6. Cek hasil fase ini ✅

1. Pastikan Docker Postgres jalan: `docker compose ps` → `db` status `healthy`.
2. Jalanin server:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Buka terminal lain, cek tabel yang terbentuk:
   ```bash
   docker compose exec db psql -U app -d house_price -c '\dt'
   ```
   Harusnya muncul:
   ```
    public | predictions | table | app
    public | users       | table | app
   ```
4. Cek struktur kolom tabel predictions:
   ```bash
   docker compose exec db psql -U app -d house_price -c '\d predictions'
   ```

> Kalau memakai SQLite: tabel otomatis dibuat di file `house_price.db` di folder project.

---

## 7. Yang kamu pelajari di fase ini

- PostgreSQL via Docker Compose + volume agar data tidak hilang.
- SQLAlchemy 2.0 modern: `Mapped[...]`, `mapped_column`, `DeclarativeBase`.
- Dependency `get_db` (generator) = pola session-per-request.
- `lifespan` untuk kode startup (create_all).
- Relasi 1-to-many `User` ↔ `Prediction`.

---

## 🎯 Latihan

1. Tambahkan satu kolom baru di `Prediction` (misal `catatan: str | None`) lalu
   restart server. Perhatikan: `create_all` **tidak** menambahkan kolom ke tabel yang
   sudah ada — lihat `\d predictions`, kolom baru tidak muncul. Inilah kenapa nanti kita
   butuh migrasi (Alembic).
2. (Opsional) Coba konek manual dari Python:
   ```bash
   python -c "from app.core.database import SessionLocal; from app.models import User; u=User(email='a@b.com', full_name='Test', hashed_password='x'); s=SessionLocal(); s.add(u); s.commit(); print('user id', u.id); s.close()"
   ```
   Lalu cek `docker compose exec db psql -U app -d house_price -c 'select * from users;'`

> Database sudah nyambung! Lanjut ke **[Fase 4 — Auth JWT](../fase-4-auth-jwt/README.md)** 👈
> Saatnya mengamankan API dengan login & token.
