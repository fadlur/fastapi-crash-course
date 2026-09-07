FROM python:3.12-slim

# Output Python tidak di-buffer & log langsung tampil di Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# curl dipakai untuk healthcheck dari docker-compose
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 1) Install dependency DULU (jarang berubah -> memanfaatkan cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Salin kode aplikasi
COPY . .

# 3) Latih model saat build -> image self-contained (berisi model.joblib)
RUN python -m app.ml.trainer

EXPOSE 8000

# Tanpa --reload! Ini mode produksi.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
