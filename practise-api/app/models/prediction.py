from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # ---- Fitur input (dikirim client) ----
    luas_tanah: Mapped[float] = mapped_column(Float)
    luas_bangungan: Mapped[float] = mapped_column(Float)
    jumlah_kamar: Mapped[int] = mapped_column(Integer)
    jumlah_kamar_mandi: Mapped[int] = mapped_column(Integer)
    skor_lokasi: Mapped[float] = mapped_column(Float)
    umur_bangunan: Mapped[int] = mapped_column(Integer)
    catatan: Mapped[str] = mapped_column(String(255))

    # ---- Hasil prediksi (dari model ML, Fase 5) -----
    harga_prediksi: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="predictions")