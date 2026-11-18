# SQL siap-import (database albis_db)

Dibuat dari hasil `flask db upgrade` (revisi `20261017_0003`) pada database bersih, lalu diuji: dimuat ke database kosong,
`db current` = head, `db check` tanpa selisih, `db upgrade` tidak melakukan apa-apa, dan aplikasi jalan dengan role runtime.

| File | Isi |
|---|---|
| `01_schema.sql` | 14 tabel + indeks + constraint (tanpa OWNER/GRANT, cocok untuk user mana pun) |
| `02_data_awal.sql` | versi migrasi (`alembic_version`), 8 kategori, 8 produk pembuka beserta gambarnya |

Admin **tidak** ada di sini (password tidak boleh ikut zip). Buat lewat `create-admin`.

## Pakai (hanya pada database KOSONG)
Nama container/user/database sesuaikan dengan compose-mu (contoh: `albis-db`, `postgres`, `albis_antique`).
```bash
docker exec -i albis-db psql -U postgres -d albis_antique -v ON_ERROR_STOP=1 < database/01_schema.sql
docker exec -i albis-db psql -U postgres -d albis_antique -v ON_ERROR_STOP=1 < database/02_data_awal.sql
docker exec -it albis-web python -m flask --app run create-admin
```
PowerShell (tanpa `<`):
```powershell
Get-Content database/01_schema.sql -Raw | docker exec -i albis-db psql -U postgres -d albis_antique -v ON_ERROR_STOP=1
Get-Content database/02_data_awal.sql -Raw | docker exec -i albis-db psql -U postgres -d albis_antique -v ON_ERROR_STOP=1
```

## WAJIB setelah import
Dump ini berhenti di revisi `20261017_0003`. Setelah memuat `01_schema.sql` dan `02_data_awal.sql`, jalankan
`python -m flask --app run db upgrade` agar revisi berikutnya (status akun, verifikasi email, sesi, Midtrans) ikut terpasang.

## Catatan
- **Jangan** import ke database yang sudah punya tabel (mis. dari versi lama). Cek dulu `select * from alembic_version;`
  lalu pakai `python -m flask --app run db upgrade` agar data lama aman.
- Tanpa produk pembuka: jalankan hanya `01_schema.sql`, lalu `python -m flask --app run db stamp head` dan
  `python -m flask --app run seed-catalog --tanpa-produk`.
- Jalur resmi tetap `db upgrade`; file SQL ini jalan pintas supaya tidak perlu menjalankan migrasi manual.
