# Dockerfile untuk Backend FastAPI Kasirku POS
FROM python:3.12-slim

WORKDIR /app

# Install dependensi sistem jika diperlukan untuk build lib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Salin berkas requirements dan pasang pustaka
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin kode aplikasi backend
COPY . .

# Port default FastAPI
EXPOSE 8000

# Health check container
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Perintah menjalankan Uvicorn
CMD ["uvicorn", "app.utama:aplikasi", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
