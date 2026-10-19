# ======================================================================
# Image aplikasi Flask Albis Antique (gunicorn). Tidak dibuka ke luar:
# nginx yang menerima trafik lalu meneruskannya ke sini (port 5000).
# ======================================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Layer dependensi di-cache; versi dipatok di requirements.txt (rantai pasok, OWASP A03).
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Jalan sebagai user biasa. Hanya instance/ (upload foto produk & bukti bayar) yang boleh ditulis.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/instance/uploads/products /app/instance/uploads/payments \
    && chown -R appuser:appuser /app/instance
USER appuser

EXPOSE 5000

# Bind 0.0.0.0 agar terjangkau nginx lewat jaringan Docker. Batas request mencegah header/URL raksasa.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", \
     "--limit-request-line", "4094", "--limit-request-fields", "60", \
     "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
