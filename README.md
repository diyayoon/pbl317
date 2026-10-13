# Albis Antique

Prototipe e-commerce single-store untuk koleksi barang antik dan vintage, menggunakan Flask/Jinja dengan visual frost-blue, aksen gold, serta ilustrasi Elfaria di atas footer publik.

## Teknologi
- Python dan Flask
- Jinja templates
- HTML/CSS/JavaScript
- Flask-Login, Flask-WTF, Flask-SQLAlchemy, Flask-Migrate
- PostgreSQL melalui `psycopg[binary]` (konfigurasi koneksi tersedia; integrasi data produk/transaksi masih perlu diselesaikan)

## Jalankan secara lokal (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

Buka `http://127.0.0.1:5000/`.

Jika Windows Smart App Control memblokir ekstensi native SQLAlchemy, lihat langkah khusus di [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Jangan menonaktifkan kebijakan keamanan hanya untuk mengatasi masalah ini.

## Akun demo lokal

Akun demo tersedia untuk pengujian antarmuka selama `DEMO_AUTH_ENABLED=1`. Kredensial ada di [`docs/AKUN-DEMO-LOKAL.md`](docs/AKUN-DEMO-LOKAL.md). Akun demo bukan autentikasi produksi.

## Struktur proyek

```text
app/
├── blueprints/   # route main, auth, customer, admin
├── models/       # model domain/database
├── services/     # layanan checkout, pembayaran, laporan
├── utils/        # validasi, keamanan, upload, decorator
├── templates/    # Jinja templates dan partials
└── static/       # CSS, JavaScript, gambar, kategori

docs/             # desain, keamanan, deployment, dan status uji
tests/            # pengujian otomatis
```

## Status fitur

- Halaman publik, katalog, detail produk, login/register demo, dan workspace customer/admin merupakan prototipe UI.
- Registrasi belum menyimpan akun ke database.
- Data katalog masih dummy; keranjang/wishlist menggunakan penyimpanan browser pada bagian UI.
- Checkout, pembayaran, dan laporan belum boleh dianggap sebagai alur transaksi produksi hanya berdasarkan tampilan.

## Dokumentasi
- [`docs/RIWAYAT-PERUBAHAN.md`](docs/RIWAYAT-PERUBAHAN.md) — ringkasan revisi sebelumnya.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — menjalankan lokal dan Docker, termasuk workaround SQLAlchemy pada Windows yang terdampak.
- [`docs/STATUS-PENGUJIAN.md`](docs/STATUS-PENGUJIAN.md) — cakupan audit dan batas pengujian.
- [`docs/erd-revisi.md`](docs/erd-revisi.md) — rancangan entitas dan relasi.
- [`docs/oop-design.md`](docs/oop-design.md) — rancangan OOP.
- [`docs/security-requirements.md`](docs/security-requirements.md) — baseline keamanan.
- [`docs/image-sources.md`](docs/image-sources.md) — sumber foto katalog.
- [`docs/UI_INTERACTION_POLISH.md`](docs/UI_INTERACTION_POLISH.md) — interaksi antarmuka.

## Sebelum produksi

Gunakan `ProductionConfig`, secret dari environment, HTTPS, cookie secure, autentikasi berbasis database, validasi dan otorisasi server-side, CSRF, validasi upload, rate limiting, audit log, backup, migrasi, serta pengujian keamanan.
