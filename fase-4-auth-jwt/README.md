# Fase 4 — Auth: Register, Login, JWT 🔐

**Tujuan fase ini:**

- Paham cara kerja hashing password & JWT (bukan sekadar ikut tutorial).
- Membuat endpoint `register`, `login`, dan `me`.
- Melindungi endpoint dengan dependency `get_current_user`.

> Hampir semua aplikasi (termasuk tesis) butuh auth. Bagian yang sering bikin bingung
> bukan kode-nya, tapi **konsepnya**. Kita bahas konsep dulu, baru kode.

---

## 1. Konsep: Password & Token

### Kenapa password tidak boleh disimpan mentah?

Kalau database bocor, password user ikut bocor. Solusinya **hash**: password diubah jadi
string acak searah (tidak bisa dibalik). Saat login, kita hash ulang input user lalu
bandingkan.

```
daftar:  password "rahasia123"  →  hash "$2b$12$XkYz..."   ← disimpan
login:   input "rahasia123"      →  hash lagi → cocok? → boleh masuk
```

Kita pakai **bcrypt** (library khusus hashing password, sudah termasuk salt otomatis
untuk menangkal serangan rainbow table).

### Kenapa token JWT?

HTTP itu "tanpa ingatan" (stateless). Setelah login, bagaimana server tahu request
berikutnya dari user yang sama? Jawabannya: server memberi **token** — kartu akses yang
ditandatangani. Client kirim token itu di tiap request.

```
JWT = header.payload.signature
      │        │        └─ ditandatangani SECRET_KEY (tidak bisa dipalsukan)
      │        └─ isi: sub (id user), exp (kadaluarsa)
      └─ algoritma (HS256)
```

**Kunci keamanan JWT ada di `SECRET_KEY`.** Server menandatangani token dengan secret ini.
Kalau secret bocor, orang bisa membuat token palsu → semua akun bisa diambil alih.

> 🧠 **Kenapa stateless itu bagus?** Server tidak perlu menyimpan "sesi login" di
> database/memori. Token bisa diverifikasi sendiri → mudah di-scale (banyak server).
> Ini bedanya dengan session ala Django/Flask.

---

## 2. Buat helper keamanan: `app/core/security.py`

```python
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(plain: str) -> str:
    """Hash password → string yang disimpan di DB."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Cocokkan password input dengan hash tersimpan."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """Buat JWT berisi sub (id user) + exp (kadaluarsa)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Baca & verifikasi JWT → kembalikan sub. None kalau invalid/kadaluarsa."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
```

> Perhatikan: kita **tidak** menyimpan password asli di mana pun. Kita cuma simpan
> `hashed_password` — kolom yang sudah kita buat di `User` (Fase 3).

---

## 3. Schema (Pydantic) untuk input/output auth

Buat folder `app/schemas/` dengan file kosong `__init__.py`.

**`app/schemas/user.py`**:

```python
from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # bisa terima objek ORM langsung

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
```

**`app/schemas/auth.py`**:

```python
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

> `EmailStr` butuh `email-validator` (sudah di requirements). `min_length=8` pada
> password = validasi kebijakan password di level Pydantic.

---

## 4. Dependency: siapa user yang sedang login?

Buat **`app/api/deps.py`**:

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

settings = get_settings()

# OAuth2PasswordBearer membaca header "Authorization: Bearer <token>".
# tokenUrl = endpoint login untuk tombol "Authorize" di Swagger.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tidak bisa memvalidasi kredensial",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = decode_access_token(token)
    if subject is None:
        raise credentials_error

    user = db.get(User, int(subject))
    if user is None:
        raise credentials_error

    return user
```

**Penjelasan:**

- `OAuth2PasswordBearer` = helper FastAPI yang mengambil token dari header
  `Authorization: Bearer ...`. Kalau tidak ada → otomatis 401.
- `get_current_user` = dependency yang bisa dipasang di endpoint mana pun yang ingin
  diproteksi. Alurnya: ambil token → decode → cari user di DB → return user.

---

## 5. Router auth: register, login, me

Buat **`app/api/v1/auth.py`**:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    # 1. Cek email sudah terdaftar?
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email sudah terdaftar",
        )

    # 2. Simpan user (password di-hash!)
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    # form_data.username = email (client kirim pakai form, bukan JSON)
    user = db.scalar(select(User).where(User.email == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Sukses → beri token
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def read_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Contoh endpoint terproteksi: siapa yang sedang login?"""
    return current_user
```

**Penjelasan penting:**

- **Login pakai `OAuth2PasswordRequestForm`** (bukan JSON). Ini _standar OAuth2_ dan
  membuat tombol **Authorize** di Swagger `/docs` berfungsi otomatis. Client mengirim
  `username` & `password` sebagai form data.
- Endpoint `/auth/me` kita proteksi dengan `Depends(get_current_user)` — coba akses
  tanpa token, akan dapat 401.

---

## 6. Daftarkan router auth

Update **`app/api/v1/api.py`** (timpa):

```python
from fastapi import APIRouter

from app.api.v1 import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
```

---

## 7. Cek hasil fase ini ✅

Jalankan `uvicorn app.main:app --reload` lalu buka `/docs`.

### Cara 1: lewat Swagger (paling mudah)

1. **Register** → `POST /api/v1/auth/register` → Try it out →
   ```json
   {
     "email": "demo@tes.com",
     "full_name": "Demo User",
     "password": "rahasia123"
   }
   ```
   → response 201 dengan data user (tanpa password!).
2. Klik tombol **Authorize** (kanan atas) → isi `username: demo@tes.com`,
   `password: rahasia123` → Authorize. (Ini memanggil `/auth/login` otomatis.)
3. Buka `GET /api/v1/auth/me` → Try it out → dapat data user. 🎉
4. Coba register email yang sama lagi → harusnya 409 "Email sudah terdaftar".

### Cara 2: lewat terminal (curl)

```bash
# register
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@tes.com","full_name":"Demo User","password":"rahasia123"}'

# login → dapat access_token
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d 'username=demo@tes.com&password=rahasia123'

# panggil /me dengan token
curl http://127.0.0.1:8000/api/v1/auth/me \
  -H 'Authorization: Bearer <ISI_ACCESS_TOKEN_DI_SINI>'
```

> Coba juga `curl http://127.0.0.1:8000/api/v1/auth/me` **tanpa** header → dapat 401.
> Itu bukti endpoint-nya sudah terproteksi.

---

## 8. Yang kamu pelajari di fase ini

- Hashing password (bcrypt) vs menyimpan mentah.
- JWT: isi, signature, `SECRET_KEY`, dan kadaluarsa (`exp`).
- `OAuth2PasswordBearer` + `OAuth2PasswordRequestForm`.
- Pola dependency `get_current_user` untuk proteksi endpoint.

---

## 🎯 Latihan

1. Ubah `ACCESS_TOKEN_EXPIRE_MINUTES=1` di `.env`, login, tunggu 1 menit, lalu panggil
   `/me` → harusnya 401 (token kadaluarsa). Kembalikan ke 60.
2. Buat endpoint baru `GET /auth/profile` yang mengembalikan email + full_name user yang
   login (proteksi pakai `get_current_user`).
3. Buka database & lihat bahwa kolom `hashed_password` terisi hash, bukan password asli:
   ```bash
   docker compose exec db psql -U app -d house_price -c 'select email, hashed_password from users;'
   ```

> Auth beres! Lanjut ke **[Fase 5 — Integrasi Model ML](../fase-5-model-ml/README.md)** 👈
> Bagian paling mirip tesis kamu: memanggil model ML dari API.
