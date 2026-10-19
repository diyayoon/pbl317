# Panduan deploy (Portainer / Docker Compose)

Database **albis_db** berada di VM PostgreSQL (lewat Tailscale/VLAN). Stack ini hanya berisi `web` (Flask) dan `nginx`.

## 1. Siapkan database (sekali, di VM PostgreSQL)
```sql
CREATE ROLE albis_owner LOGIN PASSWORD '<kuat-1>';     -- pemilik skema, hanya untuk migrasi
CREATE ROLE albis_app   LOGIN PASSWORD '<kuat-2>';     -- dipakai aplikasi (tanpa DDL)
CREATE DATABASE albis_db OWNER albis_owner;
\c albis_db
GRANT USAGE ON SCHEMA public TO albis_app;
GRANT CREATE ON SCHEMA public TO albis_owner;
ALTER DEFAULT PRIVILEGES FOR ROLE albis_owner IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO albis_app;
ALTER DEFAULT PRIVILEGES FOR ROLE albis_owner IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO albis_app;
```
Pastikan `pg_hba.conf` hanya mengizinkan alamat Tailscale/VLAN server web untuk `albis_db`.

## 2. Environment stack di Portainer
| Variabel | Isi |
|---|---|
| `SECRET_KEY` | `python -c "import secrets;print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `postgresql+psycopg://albis_app:<kuat-2 URL-encoded>@<host-db>:5432/albis_db` |
| `MIGRATION_DATABASE_URL` | sama tetapi `albis_owner` (hanya dipakai service `migrate`) |
| `APP_HTTP_PORT` | `8081` (bebas asal tidak bentrok) |
| `PAYMENT_BANK_NAME/ACCOUNT/HOLDER`, `PAYMENT_QRIS_NOTE` | data rekening toko yang tampil ke customer |
| `SESSION_COOKIE_SECURE` | `1` (default). Isi `0` **hanya** untuk uji lewat `http://IP:PORT` |

> Pakai metode **Repository** (Git) di Portainer supaya `build: context` dan folder `nginx/` ikut terbaca.

## 3. Jalankan
1. Deploy stack (web → nginx; web dinyatakan sehat lewat `/health`, tidak bergantung database).
2. Migrasi (sekali, dan setiap ada migrasi baru): `docker compose --profile tools run --rm migrate`
   *Alternatif tanpa migrasi:* import `database/01_schema.sql` + `02_data_awal.sql` ke database kosong (lihat `database/README.md`).
3. Data awal & admin pertama (di container web):
   ```bash
   docker compose exec web python -m flask --app run seed-catalog        # tambah --tanpa-produk bila tak mau koleksi pembuka
   docker compose exec web python -m flask --app run create-admin
   ```
4. Cek: `curl http://<host>:8081/health` (aplikasi) dan `/health/db` (database).

## 4. Cloudflare Tunnel / HTTPS
Arahkan tunnel ke `http://<host>:8081`. Cookie sesi bertanda `Secure`, jadi login hanya berfungsi lewat domain HTTPS.
Nginx meneruskan `CF-Connecting-IP` sebagai IP klien dan `X-Forwarded-Proto: https` (HSTS aktif otomatis).

## 5. Perawatan
- Pesanan kedaluwarsa dibersihkan otomatis saat halaman pesanan/admin dibuka; untuk jadwal tetap:
  `docker compose exec web python -m flask --app run expire-orders` (cron host, mis. tiap 30 menit).
- Bersihkan catatan percobaan login lama: `... purge-security-events` (mis. harian).
- Backup: `pg_dump albis_db` + volume `instance_data` (foto produk & bukti bayar).
- Perbarui dependensi terencana: `pip-audit -r requirements.txt`, uji, lalu patok ulang versi.
