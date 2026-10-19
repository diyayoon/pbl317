# Albis Antique — Frontend Only (Deployment Ready)

Aset visual FE, Docker Compose + Nginx + Gunicorn, serta `python run.py` dapat digunakan untuk preview lokal.
`.env` tidak boleh di-commit; gunakan `.env.example` sebagai template.

## Jalankan lokal

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Ganti SECRET_KEY di .env dengan nilai acak sebelum penggunaan non-lokal
python run.py
```

Buka `http://127.0.0.1:5000`.

## Jalankan dengan Docker Compose

```powershell
Copy-Item .env.example .env
# Edit SECRET_KEY pada .env
docker compose up -d --build
```

Akses `http://localhost:8081` (atau port `APP_HTTP_PORT` di `.env`).
