# 🏠 House Price Prediction API

Contoh **case study real project FastAPI tingkat produksi** dari course
"FastAPI Crash Course — dari Nol sampai Deploy Produksi".

API ini mencerminkan pola tesis khas: **SQLAlchemy + PostgreSQL, Pydantic v2, model ML
(joblib), auth JWT**, lalu siap dideploy ke **VPS + Docker**.

## Fitur

| Method | Path                       | Keterangan                                        |
| ------ | -------------------------- | ------------------------------------------------- |
| POST   | `/api/v1/auth/register`    | Daftar akun baru                                  |
| POST   | `/api/v1/auth/login`       | Login (form) → dapat `access_token`               |
| GET    | `/api/v1/auth/me`          | Lihat profil sendiri (perlu token)                |
| POST   | `/api/v1/predictions`      | Prediksi harga rumah → simpan ke DB (perlu token) |
| GET    | `/api/v1/predictions`      | Riwayat prediksi sendiri, pagination              |
| DELETE | `/api/v1/predictions/{id}` | Hapus riwayat sendiri                             |
| GET    | `/api/v1/health`           | Status aplikasi + model                           |

## Quickstart (lokal)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# (opsional) jalankan Postgres via Docker, lalu sesuaikan .env
cp .env.example .env

# latih model ML dummy
python -m app.ml.trainer

# jalankan server
uvicorn app.main:app --reload
```

Buka **http://127.0.0.1:8000/docs**.

> Tanpa Postgres? Set `DATABASE_URL=sqlite+pysqlite:///./house_price.db` di `.env`.

## Test

```bash
python -m pytest -v
```

## Docker

```bash
docker compose up -d --build     # API + PostgreSQL
```

## Deploy produksi (VPS + Caddy + HTTPS)

Lihat panduan lengkap di folder **`fase-8-deploy-produksi`** pada course ini.
Intinya:

```bash
cp .env.prod.example .env   # isi domain, secret, password DB
docker compose -f docker-compose.prod.yml up -d --build
```

## Struktur

```
app/
├── main.py            # titik masuk FastAPI + lifespan
├── core/              # config, database, security
├── models/            # SQLAlchemy ORM (users, predictions)
├── schemas/           # Pydantic v2 (request/response)
├── api/               # router + dependency auth
│   └── v1/            # health, auth, prediction
├── services/          # logika bisnis (ml_service, prediction_service)
└── ml/                # trainer + artifacts/model.joblib
tests/                 # pytest
Dockerfile
docker-compose.yml
docker-compose.prod.yml
Caddyfile
```
