# ======================================================================
# Dockerfile aplikasi Flask Albis Antique (dijalankan oleh gunicorn).
# Container ini TIDAK dibuka ke luar; nginx (folder nginx/) yang menerima
# trafik di port 8080 lalu meneruskannya ke sini.
# ======================================================================

# ===== IMAGE DASAR =====
FROM python:3.13-slim

# ===== PENGATURAN PYTHON =====
# Tanpa file .pyc dan tanpa buffer output, supaya log langsung terlihat di Portainer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ===== DEPENDENSI (LAYER DI-CACHE) =====
# requirements.txt disalin lebih dulu agar layer ini tidak dibangun ulang saat hanya kode yang berubah.
# gunicorn belum ada di requirements.txt, jadi dipasang terpisah.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "gunicorn>=23,<26"

# ===== KODE APLIKASI =====
# venv, .git, tests, dan .env dikecualikan lewat .dockerignore.
COPY . .

# ===== JALANKAN SEBAGAI USER BIASA (BUKAN ROOT) =====
# Hanya folder instance yang perlu bisa ditulis (foto produk yang diupload admin).
# Folder ini juga dipasang sebagai volume, jadi foto tidak hilang saat container dibuat ulang.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/instance/uploads/products \
    && chown -R appuser:appuser /app/instance
USER appuser

EXPOSE 5000

# ===== PERINTAH START =====
# run:app = objek `app` di run.py. Bind ke 0.0.0.0 supaya bisa dijangkau nginx lewat jaringan Docker.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "run:app"]
