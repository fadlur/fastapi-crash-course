from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Semua konfigurasi aplikasi dalam satu tempat.

    Urutan prioritas nilai: environment variable > file .env > default di sini.
    """

    model_config = SettingsConfigDict(
        env_file=".env",       # baca nilai dari file .env
        env_file_encoding="utf-8",
        extra="ignore",        # abaikan variable lain di environment
    )

    # ----- Aplikasi -----
    APP_NAME: str = "House Price Prediction API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # ----- CORS -----
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ----- Database -----
    DATABASE_URL: str = "sqlite+pysqlite:///./house_price.db"

    # ----- Auth -----
    SECRET_KEY: str = "ganti-ini-sebelum-produksi"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ----- Model ML -----
    MODEL_PATH: str = "app/ml/artifacts/model.joblib"
    MODEL_VERSION: str = "v1.0.0"


@lru_cache
def get_settings() -> Settings:
    """Dipanggil berkali-kali tapi hasilnya di-cache (dibaca 1x saja)."""
    return Settings()
