# Fase 7 — Docker: Kemas Aplikasi Jadi Container 🐳

**Tujuan fase ini:**

- Memahami Docker: image vs container, dan kenapa produksi wajib pakai ini.
- Membuat `Dockerfile` yang benar untuk aplikasi FastAPI + ML.
- Menjalankan API + PostgreSQL lewat `docker-compose.yml`.
- Paham kenapa `--reload` tidak dipakai di container produksi.

> Sampai fase ini kamu jalanin API di laptop dengan venv (`uvicorn --reload`). Sekarang
> kita **kemas** aplikasi supaya bisa jalan di mana saja — termasuk VPS di Fase 8.

---

## 1. Konsep: Image vs Container

Bayangkan image itu **cetakan kue**, container itu **kue hasil cetakan**:

| Istilah       | Perumpamaan        | Sifat                                 |
| ------------- | ------------------ | ------------------------------------- |
| **Image**     | Cetakan/resep jadi | Statis, tidak berubah, bisa dibagikan |
| **Container** | Kue yang jalan     | Hidup, bisa di-start/stop/hapus       |

Alur praktisnya:

1. Kamu tulis `Dockerfile` (resep cara membuat image).
2. `docker build` → menghasilkan **image** (misal `house-price-api`).
3. `docker run` / `docker compose up` → image dijalankan sebagai **container**.

**Kenapa ini wajib di produksi?** Karena container membungkus **kode + Python + semua
dependency + file model** jadi satu paket yang identik di laptop, di server, di mana pun.
Tidak akan ada lagi kalimat "kok di laptop saya jalan?" 😄

---

## 2. Konsep: `Dockerfile` yang baik untuk FastAPI + ML

Poin penting yang harus dipahami:

1. **Layer caching** — perintah yang jarang berubah (install dependency) ditaruh lebih
   dulu, supaya saat kamu ubah kode, Docker tidak perlu install ulang.
2. **Model di-build ke dalam image** — file `model.joblib` ikut di-generate saat build
   (`python -m app.ml.trainer`). Hasilnya image **self-contained**.
3. **Jangan menyalin rahasia** — `.env` di-exclude lewat `.dockerignore`.
4. **Gunakan `uvicorn` tanpa `--reload`** — di dalam container, kode sudah "final".
   Restart dilakukan dengan build ulang image (bukan auto-reload).

### Buat file **`Dockerfile`**:

```dockerfile
FROM python:3.12-slim

# Supaya output Python tidak di-buffer & log langsung tampil di Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# curl dipakai untuk healthcheck (dari docker-compose)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 1) Install dependency DULU (jarang berubah → memanfaatkan cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Salin kode aplikasi
COPY . .

# 3) Latih model saat build → image berisi model.joblib (self-contained)
RUN python -m app.ml.trainer

EXPOSE 8000

# Tanpa --reload! Ini mode produksi.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Penjelasan perintah:**

- `FROM python:3.12-slim` → gambar dasar resmi Python yang ringan.
- `WORKDIR /app` → semua perintah selanjutnya dijalankan di folder `/app`.
- `COPY requirements.txt .` → salin file requirements dulu.
- `RUN pip install ...` → install dependency.
- `COPY . .` → salin sisa kode.
- `RUN python -m app.ml.trainer` → **model ML dibuat saat build image**.
- `CMD [...]` → perintah saat container start (tidak pakai `--reload`).

### Buat file **`.dockerignore`** (biar image tidak bengkak & rahasia tidak bocor):

```gitignore
.venv
__pycache__
*.pyc
.pytest_cache
.git
.env
.env.*
tests
app/ml/artifacts/*.joblib   # jangan salin model lama; trainer akan buat saat build
.DS_Store
```

> Kenapa `app/ml/artifacts/*.joblib` di-ignore? Karena kita mau model **dibuat fresh
> saat build** (baris `RUN python -m app.ml.trainer`), bukan menyalin file model lama
> yang mungkin tidak sinkron dengan kode.

---

## 3. Docker Compose: API + Database dalam satu perintah

Buat/update **`docker-compose.yml`** (timpa versi Fase 3 yang hanya berisi `db`):

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app_password
      POSTGRES_DB: house_price
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d house_price"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: .
    depends_on:
      db:
        condition: service_healthy # tunggu db sehat dulu baru start api
    environment:
      # Di dalam jaringan docker, host database = nama service "db"
      DATABASE_URL: postgresql+psycopg://app:app_password@db:5432/house_price
      SECRET_KEY: ${SECRET_KEY:-dev-secret-jangan-untuk-produksi}
      APP_ENV: development
      DEBUG: "true"
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

**Penjelasan konsep:**

- **`depends_on: condition: service_healthy`** → API baru start setelah PostgreSQL benar
  benar siap. Ini menyelesaikan masalah "API start sebelum DB" yang sering terjadi.
- **`DATABASE_URL=...@db:5432/...`** → di dalam jaringan Docker, `db` adalah **hostname**
  (nama service), bukan `localhost`. Ini yang membedakan config lokal vs container.
- **`${SECRET_KEY:-default}`** → pakai nilai env `SECRET_KEY` dari shell kamu, kalau
  tidak ada pakai default. (Kita bahas secret yang benar di Fase 8.)
- **`healthcheck`** → Docker mengecek `/api/v1/health` tiap 10 detik. Berguna untuk
  status & auto-restart.
- `.env` **tidak** ikut ke container (di-dockerignore), jadi semua nilai penting
  dioper lewat `environment:` atau env var.

---

## 4. Jalankan stack

```bash
# build image + start db & api
docker compose up -d --build

# lihat status
docker compose ps
```

Buka **http://localhost:8000/docs** — API kamu sekarang jalan **di dalam container**!

Cek log & healthcheck:

```bash
docker compose logs -f api        # log API (Ctrl+C untuk keluar)
docker compose ps                 # status container (harusnya healthy)
curl http://localhost:8000/api/v1/health
```

> 🧠 **Perhatikan alurnya:** `docker compose up -d --build` → build image (termasuk
> melatih model!) → start container db → tunggu healthy → start container api. Semua
> otomatis. Inilah pola deploy yang nanti kamu pakai di VPS — bedanya cuma di server.

---

## 5. Update kode di dunia container

Karena kode **disalin ke dalam image** (bukan di-mount dari folder), tiap kali ubah kode
kamu harus **build ulang**:

```bash
docker compose up -d --build api
```

Ini beda dengan development lokal (`--reload`). Memang sedikit lebih ribet, tapi ini
persis perilaku produksi: **setiap rilis = image baru**. Di Fase 8 kamu akan melihat
alur deploy yang sama.

---

## 6. Cek hasil fase ini ✅

1. `docker compose ps` → `api` dan `db` status **healthy** (atau running).
2. `curl http://localhost:8000/api/v1/health` → `{"status":"ok",...,"model_ready":true}`.
3. Register + login + predict di `/docs` **masih jalan** (data tersimpan di Postgres
   dalam volume `pgdata`).
4. Coba matikan semua: `docker compose down` — lalu `up -d` lagi. **Data tetap ada**
   karena disimpan di volume (ini keajaiban volume Docker).

---

## 7. Yang kamu pelajari di fase ini

- Image vs container, dan alur build → run.
- `Dockerfile` optimal untuk FastAPI + ML (cache layer + model di-build).
- `.dockerignore` untuk mencegah rahasia bocor & image bengkak.
- Compose: koordinasi `db` + `api`, healthcheck, volume.
- Update kode = rebuild image (pola produksi).

---

## 🎯 Latihan

1. Hapus image lalu build dari nol, catat waktu build-nya. Ubah satu baris kode, build
   lagi — perhatikan build jadi **jauh lebih cepat** (cache layer).
2. Jalankan `docker compose down -v` (hati-hati: `-v` menghapus volume/data) dan lihat
   semua data hilang. Ini pelajaran: **volume itu tempat data; jangan asal `down -v` di
   produksi!**
3. Buka log container saat start — pastikan ada baris "Model ML v1.0.0 berhasil dimuat".

> Container beres! Ini bagian paling kamu tunggu → **[Fase 8 — Deploy Produksi di VPS](../fase-8-deploy-produksi/README.md)** 🚀
