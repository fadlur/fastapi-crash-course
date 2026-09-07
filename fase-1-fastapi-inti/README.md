# Fase 1 — Inti FastAPI: Routing, Parameter, Pydantic, Error 🧠

**Tujuan fase ini:**

- Memahami _cara berpikir_ FastAPI (type hint = kontrak).
- Menguasai path param, query param, request body, dan validasi.
- Menguasai response model, status code, dan error handling.

> Fase ini yang paling penting buat **memahami FastAPI-nya sendiri**. Kita pakai contoh
> kecil dulu (bukan project besar) biar konsepnya nempel. Di Fase 2 baru kita bikin
> project case study-nya.

---

## 1. Prinsip emas FastAPI: "Kode kamu = dokumentasi = validasi"

FastAPI menggunakan **type hint Python** untuk menentukan:

1. Apa yang boleh masuk (validasi otomatis).
2. Bentuk response-nya (serialisasi otomatis).
3. Dokumentasi di `/docs` (otomatis).

Artinya, kalau kamu deklarasi parameter dengan tipe, FastAPI langsung tahu harus
dari mana datanya diambil (path, query, atau body). **Ini konsep kunci** yang membedakan
FastAPI dari Flask.

---

## 2. Path parameter vs Query parameter

Buat file `main.py` baru (timpa yang Hello World) supaya kita bereksperimen:

```python
from fastapi import FastAPI

app = FastAPI()


# ---------- PATH PARAMETER ----------
# Bagian dari URL:  /rumah/123
@app.get("/rumah/{rumah_id}")
def get_rumah(rumah_id: int):
    # FastAPI otomatis: 123 -> int. Kalau dikirim "abc" -> error 422 otomatis
    return {"rumah_id": rumah_id, "pesan": "detail rumah"}


# ---------- QUERY PARAMETER ----------
# Tanda ? di URL:  /cari?kota=Bandung&max_harga=1000000000
@app.get("/cari")
def cari_rumah(
    kota: str,                 # wajib: /cari?kota=...
    max_harga: int = 1_000_000_000,  # opsional, punya default
):
    return {"kota": kota, "max_harga": max_harga}
```

### 🔍 Cara kerjanya — ini penting!

| Deklarasi                        | Data dari mana? | Contoh URL                     |
| -------------------------------- | --------------- | ------------------------------ |
| `rumah_id: int` di dalam `{...}` | **Path**        | `/rumah/123`                   |
| `kota: str` (bukan di `{}`)      | **Query**       | `/cari?kota=Bandung`           |
| `max_harga: int = ...`           | Query opsional  | `/cari?kota=X` (pakai default) |

Coba di browser:

- `http://127.0.0.1:8000/rumah/999`
- `http://127.0.0.1:8000/rumah/abc` → **error 422** (validasi otomatis menolak, karena
  `abc` bukan angka). _Perhatikan: ini bukan error 500 — FastAPI menolak di gerbang,
  bukan crash di dalam._
- `http://127.0.0.1:8000/cari?kota=Bandung`
- `http://127.0.0.1:8000/cari` → **422**, karena `kota` tidak punya default.

> 🧠 **Paham produksi:** error 422 itu dari _validation layer_ (Pydantic). Di produksi,
> client yang salah kirim data dapat 422 — bukan 500. Bedanya penting untuk debugging:
> 422 = salah client, 500 = salah server kita.

---

## 3. Request body dengan Pydantic

Kalau datanya banyak & kompleks (misal fitur rumah), lebih enak dikirim sebagai **body**
(JSON), bukan query string. Di FastAPI, body didefinisikan dengan **Pydantic model**.

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


# ---- Pydantic model = "kontrak" data yang boleh masuk ----
class FiturRumah(BaseModel):
    luas_tanah: float = Field(gt=0, description="Luas tanah m²")
    luas_bangunan: float = Field(gt=0)
    jumlah_kamar: int = Field(ge=1, le=20)
    skor_lokasi: float = Field(ge=0, le=10)  # nilai 0-10


# Pydantic model untuk response (kita kontrol apa yang keluar)
class PrediksiResponse(BaseModel):
    luas_tanah: float
    skor_lokasi: float
    estimasi_harga: float


@app.post("/prediksi", response_model=PrediksiResponse)
def prediksi_harga(fitur: FiturRumah):
    # Di sini nanti kita panggil model ML (Fase 5). Untuk sekarang: rumus kasar.
    estimasi = (fitur.luas_tanah * 2_500_000) + (fitur.skor_lokasi * 100_000_000)
    return PrediksiResponse(
        luas_tanah=fitur.luas_tanah,
        skor_lokasi=fitur.skor_lokasi,
        estimasi_harga=estimasi,
    )
```

### Penjelasan konsep:

- **`class FiturRumah(BaseModel)`** → Pydantic v2. Field di dalamnya **wajib** kecuali
  ada default.
- **`Field(gt=0)`** → `gt` = greater than, `ge` = greater/equal, `le` = less/equal.
  Ini _validasi level field_.
- **`response_model=PrediksiResponse`** → FastAPI memastikan response **persis** bentuk
  ini. Field yang tidak ada di response model otomatis dibuang (tidak bocor keluar).
  Ini praktik keamanan yang bagus (misal jangan sampai `hashed_password` bocor!).

### Coba di `/docs`:

1. Buka `http://127.0.0.1:8000/docs`
2. Expand endpoint `POST /prediksi` → klik **Try it out**
3. Kirim body:
   ```json
   {
     "luas_tanah": 120,
     "luas_bangunan": 90,
     "jumlah_kamar": 3,
     "skor_lokasi": 8
   }
   ```
4. Coba kirim `jumlah_kamar: 0` atau `skor_lokasi: 15` → lihat error **422** dengan
   pesan validasi yang jelas.

---

## 4. Error handling yang benar: HTTPException

Kalau terjadi masalah _bisnis_ (bukan validasi), kita tidak boleh asal `return`, tapi
melempar `HTTPException` dengan status code yang tepat.

```python
from fastapi import FastAPI, HTTPException, status

app = FastAPI()

DATA_RUMAH = {1: "Rumah minimalis Bandung", 2: "Rumah joglo Jogja"}


@app.get("/rumah/{rumah_id}")
def get_rumah(rumah_id: int):
    if rumah_id not in DATA_RUMAH:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rumah dengan id {rumah_id} tidak ditemukan",
        )
    return {"id": rumah_id, "nama": DATA_RUMAH[rumah_id]}
```

Kenapa `raise`, bukan `return error`? Karena begitu `raise HTTPException`, FastAPI
langsung menghentikan proses dan mengirim response error yang rapi:

```json
{ "detail": "Rumah dengan id 3 tidak ditemukan" }
```

### Status code yang sering dipakai

| Kode | Konstanta FastAPI                       | Arti                                  |
| ---- | --------------------------------------- | ------------------------------------- |
| 200  | `status.HTTP_200_OK`                    | Sukses (default GET)                  |
| 201  | `status.HTTP_201_CREATED`               | Berhasil dibuat (POST)                |
| 204  | `status.HTTP_204_NO_CONTENT`            | Sukses tanpa isi (DELETE)             |
| 401  | `status.HTTP_401_UNAUTHORIZED`          | Belum login / token salah             |
| 403  | `status.HTTP_403_FORBIDDEN`             | Tidak punya akses                     |
| 404  | `status.HTTP_404_NOT_FOUND`             | Data tidak ada                        |
| 409  | `status.HTTP_409_CONFLICT`              | Bentrok (misal email sudah terdaftar) |
| 422  | _(otomatis dari Pydantic)_              | Validasi input gagal                  |
| 500  | `status.HTTP_500_INTERNAL_SERVER_ERROR` | Error di server kita                  |

---

## 5. Cek hasil fase ini ✅

1. Server jalan (`uvicorn main:app --reload`).
2. `/docs` menampilkan endpoint: `GET /rumah/{rumah_id}`, `GET /cari`,
   `POST /prediksi`.
3. Posting valid body ke `/prediksi` → dapat estimasi harga.
4. Kirim data invalid → dapat 422 dengan detail yang jelas.
5. Akses `/rumah/999` → dapat 404 dengan pesan rapih.

---

## 6. Yang kamu pelajari di fase ini

- **Type hint = kontrak**: FastAPI membaca tipe untuk routing, validasi & response.
- **Path/Query/Body parameter** dan bedanya.
- **Pydantic v2 + Field validators** sebagai lapisan validasi.
- **`response_model`** untuk mengontrol & mengamankan output.
- **`HTTPException` + status codes** untuk error handling yang benar.

---

## 🎯 Latihan (kerjakan sebelum lanjut)

Di file yang sama, tambahkan endpoint `GET /laporan` yang:

1. Menerima query `bulan: int` (wajib) dan `tahun: int = 2026`.
2. Jika `bulan` di luar 1–12 → lempar `HTTPException(400, "Bulan harus 1-12")`.
3. Return `{"bulan": bulan, "tahun": tahun, "total_prediksi": 0}`.

Verifikasi: semua case di `/docs` berjalan, termasuk yang error.

> Sudah paham inti FastAPI? Lanjut ke **[Fase 2 — Struktur Proyek](../fase-2-struktur-proyek/README.md)** 👈
> Di sana kita mulai membangun project case study yang sesungguhnya.
