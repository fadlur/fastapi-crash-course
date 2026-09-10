from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Khusus kalo pake sqlite
_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,   # cek koneksi dulu sebelum pakai (aman untuk produksi)
)

# Pabrik session: dipanggil untuk membuat 1 session per request
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    """Base untuk semua model ORM."""

def get_db():
    """Dependency FastAPI: 1 session DB per request, auto close"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()