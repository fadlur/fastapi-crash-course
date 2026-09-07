# Fase 0 — Persiapan: Environment & FastAPI Pertamamu 🛠️

**Tujuan fase ini:**

- Pasang semua tools yang dibutuhkan.
- Paham "di balik layar" FastAPI itu jalan di mana.
- Menjalankan aplikasi FastAPI pertama + melihat dokumentasi otomatisnya.

> Kalau kamu pernah jalanin FastAPI buat tesis, fase ini mungkin terasa familiar —
> tapi **baca tetap penting** karena ada beberapa konsep (ASGI, virtual env, `--reload`)
> yang sering bikin bingung di level produksi nanti.

---

## 1. Konsep singkat: Apa itu FastAPI, Uvicorn, ASGI?

Bayangkan kamu buka restoran:

- **FastAPI** = koki yang tahu resep dan melayani pesanan (request) sesuai menu.
- **Uvicorn** = pelayan/kasir yang menerima tamu di pintu dan menyampaikan pesanan ke koki.
- **ASGI** = "bahasa" standar antara pelayan dan dapur. FastAPI adalah aplikasi ASGI;
  Uvicorn adalah _ASGI server_ yang menjalankannya.

Jadi **FastAPI tidak bisa jalan sendiri** — dia butuh server (Uvicorn) untuk menerima
request HTTP dari internet. Ini bedanya dengan Django/Flask dev server: di produksi,
kamu justru butuh server yang benar (Uvicorn + nanti reverse proxy di Fase 8).

```
Browser/Postman  --HTTP-->  Uvicorn (server)  --ASGI-->  FastAPI (app)  --> response
```

> 🧠 **Catatan produksi:** banyak yang bingung karena di tutorial cuma
> `uvicorn main:app --reload`. Padahal `--reload` itu **hanya untuk development**
> (auto restart saat file berubah). Di produksi kita **tidak** pakai `--reload`
> (dibahas di Fase 7–8).

---

## 2. Cek prasyarat

Buka terminal (VS Code: `Terminal > New Terminal`), lalu jalankan:

```bash
python3 --version
# harusnya Python 3.11 ke atas, misal: Python 3.12.5

docker --version
# harusnya Docker version 2x.x.x
```

Kalau `docker` belum ada: install **Docker Desktop** dari https://www.docker.com/products/docker-desktop/
(di macOS tinggal download .dmg lalu drag ke Applications, jalankan sekali).

---

## 3. Buat project & virtual environment

Virtual environment (`venv`) itu **kamar terpisah** untuk project — jadi package yang
kamu install tidak mengotori Python global. Ini kebiasaan wajib untuk project serius.

```bash
# 1. buat folder project (buka dulu folder course ini di terminal)
cd ~/Documents/Learning/"fastapi crash course"

# 2. buat folder project case study kita
mkdir house-price-api && cd house-price-api

# 3. buat venv bernama .venv
python3 -m venv .venv

# 4. aktifkan venv (macOS/Linux)
source .venv/bin/activate
#   prompt terminal akan berubah jadi (venv) di depan

# 5. pastikan pip terbaru
python -m pip install --upgrade pip
```

> Windows pakai `.venv\Scripts\activate`. Tapi kamu di macOS, jadi pakai `source`.

---

## 4. Install FastAPI + Uvicorn

```bash
pip install "fastapi[standard]"
```

`fastapi[standard]` otomatis menginstall **uvicorn** beserta paket pendukung
(untuk sekarang anggap saja "paket lengkapnya").

Cek hasil install:

```bash
pip list | grep -E "fastapi|uvicorn|pydantic"
```

Kamu akan lihat `fastapi`, `uvicorn`, dan **`pydantic`** — ini penting! Pydantic adalah
"tulang punggung" FastAPI untuk validasi data (kamu sudah kenal Pydantic v2 dari tesis).

---

## 5. Aplikasi pertama: Hello World

Buat file bernama `main.py` di dalam `house-price-api/`:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Halo dunia! API-ku jalan 🎉"}
```

Sekarang jalankan server-nya:

```bash
uvicorn main:app --reload
```

Penjelasan perintah di atas:

- `main` = nama file `main.py`
- `app` = nama variabel `FastAPI()` di dalamnya
- `--reload` = auto-restart tiap file berubah (hanya untuk development)

Output yang kamu lihat kira-kira:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## 6. Cek hasil fase ini ✅

Buka browser ke **http://127.0.0.1:8000** → kamu lihat JSON:

```json
{ "message": "Halo dunia! API-ku jalan 🎉" }
```

Lalu buka **http://127.0.0.1:8000/docs** — ini **Swagger UI**, dokumentasi API yang
**dibuat otomatis oleh FastAPI** dari kode kamu. Di sinilah kamu bisa test semua endpoint
tanpa Postman. (Fitur ini salah satu alasan FastAPI digemari!)

Coba ubah pesan di `main.py` → simpan → karena ada `--reload`, server otomatis restart.

---

## 7. Yang kamu pelajari di fase ini

- FastAPI butuh **Uvicorn** (server ASGI) untuk melayani HTTP.
- **Virtual environment** memisahkan dependency tiap project.
- FastAPI menghasilkan **dokumentasi otomatis** di `/docs`.
- `--reload` hanya untuk development.

---

## 🎯 Latihan kecil (opsional, 2 menit)

1. Tambah endpoint `GET /halo/{nama}` yang mengembalikan `{"pesan": "Halo, {nama}!"}`.
   (Hint: pakai _path parameter_, kita bahas detail di Fase 1.)
2. Pastikan masih bisa diakses di `/docs`.

> Sudah bisa? Lanjut ke **[Fase 1 — Inti FastAPI](../fase-1-fastapi-inti/README.md)** 👈
