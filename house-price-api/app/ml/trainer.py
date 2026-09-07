"""Latih model regresi sederhana → app/ml/artifacts/model.joblib.

Untuk tesis kamu: ganti generate_data() dengan pipeline training asli
(load dataset, preprocessing, fit), lalu simpan model dengan joblib.dump.
"""
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

# Urutan fitur WAJIB sama dengan _payload_to_features di router prediksi!
FEATURE_NAMES = [
    "luas_tanah",
    "luas_bangunan",
    "jumlah_kamar",
    "jumlah_kamar_mandi",
    "skor_lokasi",
    "umur_bangunan",
]


def generate_data(n: int = 3000, seed: int = 42):
    """Buat data sintetis mirip harga rumah."""
    rng = np.random.default_rng(seed)

    luas_tanah = rng.uniform(60, 600, n)
    luas_bangunan = luas_tanah * rng.uniform(0.4, 0.8, n)
    jumlah_kamar = rng.integers(1, 6, n)
    jumlah_kamar_mandi = rng.integers(1, 4, n)
    skor_lokasi = rng.uniform(0, 10, n)
    umur_bangunan = rng.integers(0, 40, n)

    X = np.column_stack(
        [luas_tanah, luas_bangunan, jumlah_kamar,
         jumlah_kamar_mandi, skor_lokasi, umur_bangunan]
    )

    # Rumus harga "tersembunyi" + noise biar mirip data asli
    noise = rng.normal(0, 5e7, n)
    y = (
        2.5e6 * luas_tanah
        + 3.0e6 * luas_bangunan
        + 8e7 * skor_lokasi
        - 1.2e6 * umur_bangunan
        + noise
    )
    y = np.maximum(y, 5e7)
    return X, y


def main():
    X, y = generate_data()
    model = LinearRegression()
    model.fit(X, y)

    out_dir = Path(__file__).parent / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "model.joblib"
    joblib.dump(model, out_path)

    print(f"Model tersimpan di: {out_path}")
    print(f"R² score: {model.score(X, y):.4f}")


if __name__ == "__main__":
    main()
