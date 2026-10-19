# Albis Antique — Frontend Only (Deployment Ready)

Paket ini mempertahankan template HTML/Jinja, CSS, JavaScript, gambar, dan aset visual FE dari sumber. Docker Compose + Nginx + Gunicorn tetap tersedia, serta `python run.py` dapat digunakan untuk preview lokal.

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

## Batasan paket FE-only

- Tidak ada database, model, migration, service, atau business backend.
- Beranda dan katalog memakai data contoh untuk keperluan preview tampilan.
- Login, registrasi, area customer/admin, checkout, dan operasi CRUD tidak memproses data; beberapa rute hanya menampilkan pemberitahuan preview.
- Untuk deploy produksi yang benar-benar melayani transaksi, integrasikan kembali backend dan konfigurasi database. Jangan memakai secret contoh.
- `.env` tidak boleh di-commit; gunakan `.env.example` sebagai template.
