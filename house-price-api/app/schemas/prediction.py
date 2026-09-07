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
