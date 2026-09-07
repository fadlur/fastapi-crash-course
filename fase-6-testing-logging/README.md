# Fase 6 — Testing & Logging 🧪

**Tujuan fase ini:**

- Menulis automated test (pytest) untuk API kita.
- Paham `dependency_overrides` untuk test dengan database test terpisah.
- Memakai logging Python yang benar (bukan `print`).

> **Kenapa test penting untuk produksi?** Saat kamu deploy, kamu tidak bisa "coba manual"
> satu-satu. Test otomatis = jaring pengaman: sebelum deploy, jalankan test → kalau
> hijau, yakin tidak merusak apa pun. Ini yang membedakan project "tugas kuliah" dan
> project "serius".

---

## 1. Konsep: cara men-test FastAPI

FastAPI menyediakan `TestClient` (berbasis httpx) yang bisa memanggil endpoint **tanpa
harus menjalankan server sungguhan**:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
resp = client.get("/api/v1/health")
assert resp.status_code == 200
```

### Masalah: test tidak boleh merusak database asli!

Kalau test pakai PostgreSQL asli, data kita bisa kotor. Solusinya:

1. Ganti `DATABASE_URL` jadi **SQLite in-memory** (cepat, hilang sendiri).
2. Ganti dependency `get_db` lewat **`app.dependency_overrides[get_db] = ...`**.

> 🧠 `dependency_overrides` adalah fitur keren FastAPI: kita bisa **menukar dependency**
> hanya saat testing. Aplikasi tetap memakai `get_db` asli di produksi, tapi di test
> dipaksa memakai session test.

---

## 2. File test

Buat folder `tests/` dengan file kosong `__init__.py`, lalu **`tests/conftest.py`**
(file konfigurasi pytest + fixture):

```python
import os

# PENTING: set env SEBELUM import app (engine DB dibuat saat import!)
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    """Satu database SQLite in-memory untuk satu test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # agar semua koneksi memakai DB yang sama
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """TestClient yang memakai session test, bukan database asli."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()  # bersihkan setelah test
```

**Penjelasan:**

- `os.environ[...]` di atas import → memastikan engine SQLite yang terpakai, bukan
  PostgreSQL.
- `StaticPool` → untuk `:memory:` SQLite, supaya semua koneksi berbagi database yang
  sama (tanpa ini tiap koneksi dapat DB kosong sendiri).
- `dependency_overrides[get_db]` → paksa semua endpoint memakai `db_session` test.

Buat **`tests/test_health.py`**:

```python
def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app_env"] == "test"
```

Buat **`tests/test_auth.py`**:

```python
def test_register_login_me(client):
    # 1. register sukses
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "full_name": "User Tes",
            "password": "rahasia123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "user@example.com"
    assert "hashed_password" not in data  # jangan sampai bocor ke response!

    # 2. register email sama → 409
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "full_name": "User Tes",
            "password": "rahasia123",
        },
    )
    assert resp.status_code == 409

    # 3. login sukses → dapat token
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user@example.com", "password": "rahasia123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # 4. /me dengan token → sukses
    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"

    # 5. password salah → 401
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user@example.com", "password": "password-salah"},
    )
    assert resp.status_code == 401
```

Buat **`tests/test_predictions.py`**:

```python
from app.services import ml_service

VALID_BODY = {
    "luas_tanah": 120,
    "luas_bangunan": 90,
    "jumlah_kamar": 3,
    "jumlah_kamar_mandi": 2,
    "skor_lokasi": 8,
    "umur_bangunan": 10,
}


def _register_and_login(client) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "pred@example.com",
            "full_name": "Pred User",
            "password": "rahasia123",
        },
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "pred@example.com", "password": "rahasia123"},
    )
    return resp.json()["access_token"]


def test_predict_requires_auth(client):
    resp = client.post("/api/v1/predictions", json=VALID_BODY)
    assert resp.status_code == 401


def test_create_and_list_prediction(client, monkeypatch):
    # Ganti fungsi predict dengan nilai tetap (tanpa butuh model asli)
    monkeypatch.setattr(ml_service, "predict_one", lambda features: 1_250_000_000.0)

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/v1/predictions", json=VALID_BODY, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["harga_prediksi"] == 1_250_000_000.0
    assert data["model_version"] != ""

    resp = client.get("/api/v1/predictions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_invalid_input_rejected(client, monkeypatch):
    monkeypatch.setattr(ml_service, "predict_one", lambda features: 1_250_000_000.0)

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    bad_body = {**VALID_BODY, "jumlah_kamar": 99}  # > 20 → harusnya 422
    resp = client.post("/api/v1/predictions", json=bad_body, headers=headers)
    assert resp.status_code == 422
```

> 💡 `monkeypatch` adalah fixture pytest untuk "mengganti" fungsi sementara — di sini
> kita ganti `predict_one` supaya test tidak butuh model asli & hasilnya deterministik.

---

## 3. Jalankan test

Dari folder `house-price-api/`:

```bash
python -m pytest -v
```

Output yang diharapkan:

```
tests/test_health.py::test_health PASSED
tests/test_auth.py::test_register_login_me PASSED
tests/test_predictions.py::test_predict_requires_auth PASSED
...
==== 5 passed in 1.2s ====
```

Semua hijau = API kamu aman untuk dikembangkan lebih lanjut. 🎉

> 💡 Kalau mau lihat seberapa banyak kode yang ter-cover test, install pytest-cov:
>
> ```bash
> pip install pytest-cov
> python -m pytest --cov=app --cov-report=term-missing
> ```

---

## 4. Logging yang benar (bukan `print`)

Di aplikasi produksi, `print()` itu jelek karena:

- Tidak ada level (info/warning/error).
- Tidak ada konteks (file mana, kapan).
- Sulit diarahkan ke file/monitoring.

Ganti dengan modul bawaan **`logging`**:

```python
import logging

logger = logging.getLogger(__name__)   # nama = path modul, misal "app.services.ml_service"

logger.info("Model dimuat")
logger.warning("File tidak ditemukan")
logger.error("Gagal terhubung ke DB")
```

Kamu sudah memakai ini di `ml_service.py`! Sekarang tinggal aktifkan konfigurasi
logging-nya supaya level `INFO` ikut tampil.

### Update kecil: tambahkan `LOG_LEVEL` di config

Di **`app/core/config.py`**, tambahkan satu baris di bagian "Aplikasi":

```python
    LOG_LEVEL: str = "INFO"
```

### Update kecil: pasang logging di `app/main.py`

Tambahkan di bagian paling atas (setelah import `logging`), lalu setelah
`settings = get_settings()`:

```python
import logging
# ... import lain ...

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
```

Sekarang saat server start, kamu akan melihat log yang rapi, termasuk:

```
... | INFO    | app.services.ml_service | Model ML v1.0.0 berhasil dimuat (...)
```

> Di produksi (Fase 8), log ini ditangkap oleh Docker (`docker logs`) dan bisa
> dihubungkan ke sistem monitoring.

---

## 5. Bonus: Background Tasks (kerja setelah response)

Kadang kamu ingin mengerjakan sesuatu **setelah** response dikirim (misal kirim email
hasil prediksi, notifikasi, update log). FastAPI punya `BackgroundTasks`:

```python
from fastapi import BackgroundTasks


def kirim_email_hasil(user_email: str, harga: float):
    # simulasi kirim email (I/O lambat, tidak perlu ditunggu client)
    print(f"Mengirim email ke {user_email}: harga prediksi {harga}")


@app.post("/predictions")
def create_prediction(payload, background_tasks: BackgroundTasks, ...):
    ...
    background_tasks.add_task(kirim_email_hasil, user_email, harga)
    return record  # client langsung dapat response, email jalan di belakang
```

Konsepnya: **response cepat untuk client**, kerja berat dipindah ke background.
(Jangan dipakai untuk kerja yang harus dijamin sukses — untuk itu butuh _job queue_
seperti Celery/ARQ, tapi itu di luar scope course ini.)

---

## 6. Cek hasil fase ini ✅

1. Semua test lulus: `python -m pytest -v` → **5 passed**.
2. Saat start server, log INFO (termasuk "Model ML ... berhasil dimuat") terlihat.
3. Coba tambahkan test baru: akses `/predictions` user A dengan token user B harus 404.

---

## 7. Yang kamu pelajari di fase ini

- `TestClient` + fixture `client` untuk test endpoint tanpa server asli.
- `dependency_overrides` → ganti DB asli dengan SQLite in-memory saat test.
- `monkeypatch` → ganti fungsi (misal model ML) saat test.
- `logging` Python vs `print`.
- `BackgroundTasks` untuk kerja setelah response.

---

## 🎯 Latihan

1. Tulis test untuk `DELETE /predictions/{id}`: buat prediksi → hapus → 204 → coba
   hapus lagi → 404.
2. Ubah `LOG_LEVEL=DEBUG` di `.env`, restart, dan lihat log lebih detail.
3. (Menantang) Tulis test yang memastikan user A **tidak bisa** melihat prediksi milik
   user B (cek `user_id` di `list_user_predictions`).

> API kamu sudah teruji! Lanjut ke **[Fase 7 — Docker](../fase-7-docker/README.md)** 👈
> Saatnya mengemas aplikasi jadi container.
