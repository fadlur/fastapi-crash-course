from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()


DATA_RUMAH = {1: "Rumah minimalis Bandung", 2: "Rumah joglo Jogja"}

# ---------- Pydantic model = "Kontrak" data yang boleh masuk ----
class FiturRumah(BaseModel):
    luas_tanah: float = Field(gt=0, description="Luas tanah m²")
    luas_bangungan: float = Field(gt=0)
    jumlah_kamar: int = Field(ge=1, le=20)
    skor_lokasi: float = Field(ge=0, le=10) # nilai 0 - 10

# Pydantic model untuk response (kita kontrol apa yang keluar)
class PrediksiResponse(BaseModel):
    luas_tanah: float
    skor_lokasi: float
    estimasi_harga: float

@app.post("/prediksi", response_model=PrediksiResponse)
def prediksi_harga(fitur: FiturRumah):
    # Di sini nanti kita panggil model ML (Fase 5). Sekarang pake rumus kasar dulu
    estimasi = (fitur.luas_tanah * 2_500_000) + (fitur.skor_lokasi * 100_000_000)
    return PrediksiResponse(
        luas_tanah=fitur.luas_tanah,
        skor_lokasi=fitur.skor_lokasi,
        estimasi_harga=estimasi,
    )    

# ---------- PATH PARAMETER --------------
# Bagian dari URL: /rumah/123
@app.get("/rumah/{rumah_id}")
def get_rumah(rumah_id: int):
    if rumah_id not in DATA_RUMAH:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rumah dengan id {rumah_id} tidak ditemukan",
        )
    # Fast API otomatis: 123 -> int. Kalau dikirim "abc" -> error 422 otomatis
    return {"rumah_id": rumah_id, "pesan": "detail rumah"}

# ----------- QUERY PARAMETER ---------------
# Tanda ? di URL: /cari?kota=Bandung&max_harga=1000000000
@app.get("/cari")
def cari_rumah(
    kota: str,                      # wajib: /cari?kota=...
    max_harga: int = 1_000_000_000, # optional, punya default
):
    return {"kota": kota, "max_harga": max_harga}

@app.get("/laporan")
def get_laporan(
    bulan: int,
    tahun: int = 2026
):
    if bulan not in range(1, 13):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulan harus 1-12"
        )
    return {"bulan": bulan, "tahun": tahun, "total_prediksi": 0}