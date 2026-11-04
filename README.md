# Albis Antique

Toko online barang antik. **Flask (OOP: blueprint → service → model) + PostgreSQL `albis_db`**, dijalankan
dengan Docker (Nginx → Gunicorn/Flask). Semua data (produk, keranjang, pesanan, pembayaran, ulasan) tersimpan
di PostgreSQL; tidak ada data tiruan di browser.

## Peran
| Peran | Cara dibuat | Akses |
|---|---|---|
| Customer | Registrasi publik `/auth/register` (otomatis, tidak bisa memilih peran) | Katalog, keranjang, checkout, pesanan, ulasan, profil |
| Admin | Hanya lewat CLI `flask create-admin` (orang internal kelompok) | Produk, kategori, pesanan, pembayaran, refund, laporan, audit log |

## Alur
Customer: katalog → detail → keranjang → checkout → Snap Midtrans Sandbox → webhook/sinkronisasi pembayaran → diproses → dikirim → selesai → ulasan. Untuk pesanan Midtrans yang sudah dibayar tetapi belum dikirim, customer dapat mengajukan refund; admin meninjau dan gateway harus mengonfirmasi sebelum status lokal menjadi Direfund.
Pesanan yang tidak dibayar dalam `ORDER_PAYMENT_TTL_JAM` (default 24 jam) otomatis dibatalkan dan stok kembali.

## Database siap-import
`database/` berisi skema + data awal SQL hasil migrasi (alternatif dari `db upgrade`); lihat `database/README.md`.

## Preview lokal tanpa PostgreSQL (SQLite, khusus development)
Cukup untuk melihat tampilan dan mencoba alur di laptop. Data **bukan** data produksi.
```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
# .env:  APP_ENV=development  SECRET_KEY=<acak>  DATABASE_URL=sqlite:///dev.db   (file: instance/dev.db)
python -m flask --app run init-dev-db                 # buat tabel + kategori + koleksi pembuka
python -m flask --app run create-admin
python run.py                                         # http://127.0.0.1:5000
```
SQLite ditolak otomatis bila `APP_ENV=production`. Untuk uji yang setara produksi (rebutan stok, dsb.) pakai PostgreSQL lewat Docker.

## Menjalankan
Lihat [`docs/REVISI-FINAL.md`](docs/REVISI-FINAL.md) (migrasi, konfigurasi, perilaku keamanan, cara uji),
[`docs/REVISI-MIDTRANS.md`](docs/REVISI-MIDTRANS.md) (registrasi, email, dan pembayaran Midtrans sandbox), serta
[`docs/REVISI-FRONTEND-20261027.md`](docs/REVISI-FRONTEND-20261027.md) (perbaikan UI, upload kategori/ulasan, migrasi, dan checklist testing).

Lokal tanpa Docker:
```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                  # isi SECRET_KEY dan DATABASE_URL (albis_db)
python -m flask --app run db upgrade                  # pakai MIGRATION_DATABASE_URL bila ada
python -m flask --app run seed-catalog                # kategori + koleksi pembuka (opsional --tanpa-produk)
python -m flask --app run create-admin
python run.py
```

## Perintah CLI
`db-check`, `seed-catalog [--tanpa-produk]`, `create-admin` (satu-satunya cara membuat admin), `expire-orders`, `purge-security-events`, `db upgrade|check`.

## Tes
```bash
python -m pytest -q        # seluruh test suite (SQLite in-memory); lihat docs/REVISI-FINAL.md untuk uji di PostgreSQL
pip-audit -r requirements.txt && bandit -q -r app -ll
```
