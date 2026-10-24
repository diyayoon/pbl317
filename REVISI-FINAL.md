# Revisi Final Albis Antique

Dokumen ini merangkum lima revisi (verifikasi akun, kelola customer, otorisasi, timeout inaktivitas, pencarian).

## Migration (semua non-destruktif, tanpa DROP/TRUNCATE)
| Revisi | Isi |
|---|---|
| `20261024_0004` | `users.status_reason`, `users.deleted_at` (nullable) |
| `20261024_0005` | `users.is_verified` (**akun lama otomatis `true`**, akun baru `false`), `email_verified_at`, tabel `email_verification_tokens` |
| `20261024_0006` | tabel `user_sessions` (sesi sisi server) |
| `20261024_0007` | `email_verification_tokens.code_hash`, `attempts` (kode OTP email) |

Jalankan: `python -m flask --app run db upgrade` (dengan role OWNER di `MIGRATION_DATABASE_URL`). **Backup database dulu.**
`database/01_schema.sql` adalah dump lama dan **belum memuat kolom/tabel baru**; instalasi baru pakai migration, atau regenerasi dump.

## Konfigurasi (`.env`, lihat `.env.example`)
- SMTP/Gmail: aktifkan 2-Step Verification, buat **App Password**, isi `MAIL_SERVER=smtp.gmail.com`, `MAIL_PORT=587`, `MAIL_SECURITY=starttls`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`.
- `APP_BASE_URL` **wajib di produksi** (dasar tautan verifikasi; tidak memakai header Host).
- Timeout: `SESI_INAKTIF_MENIT_CUSTOMER=10`, `SESI_INAKTIF_MENIT_ADMIN=5`, `SESI_MAKS_MENIT=480`.
- Tanpa kredensial SMTP, email **tidak terkirim** (tidak ada simulasi); registrasi tetap berhasil dan user bisa kirim ulang dari halaman verifikasi.

## Perilaku utama
- **Verifikasi email (kode + tautan)**: alur: daftar → halaman "Registrasi berhasil, cek email" (`/auth/verifikasi/cek-email`: Masukkan kode, Kembali ke login, Kirim ulang) → halaman kode (`/auth/verifikasi/kode`: email tersamar, input kode, hitung mundur kirim ulang, tombol Lanjutkan aktif setelah kode lengkap). Email berisi **kode** (default 6 digit, `EMAIL_VERIFY_KODE_DIGIT`, 4–8) dan **tautan**. Kode disimpan sebagai HMAC (SECRET_KEY + id user), maksimal 5 salah (`EMAIL_VERIFY_KODE_MAX_SALAH`) lalu kode dimatikan dan wajib kirim ulang; kirim ulang membuat kode lama tak berlaku. Kode 4 digit lebih mudah ditebak (10.000 kemungkinan), jadi 6 digit lebih aman. Halaman ini bisa dipakai tanpa login hanya untuk akun yang baru mendaftar di sesi yang sama (bukan login). Token tautan: token acak 256-bit, hanya hash SHA-256 di DB, berlaku 24 jam, sekali pakai (klaim atomik), tautan baru membatalkan yang lama. Link di email membuka halaman konfirmasi; verifikasi terjadi lewat POST (pemindai tautan tidak menghabiskan token). Kirim ulang: cooldown 60 dtk, 5/jam per akun, kuota per IP. Pesan, bukti bayar, dan ulasan butuh `is_verified` (dicek di backend); login dan jelajah tetap boleh.
- **Kelola customer** (`/admin/pengguna`): aktifkan, nonaktifkan, blokir (alasan wajib), soft delete (anonimisasi, pesanan/pembayaran tetap). Hanya role `customer` yang bisa dikelola. Nonaktif/blokir/hapus menaikkan `auth_version` sehingga sesi aktif langsung gugur. Semua aksi masuk audit log.
- **Timeout**: record sesi di DB; `last_activity_at` diperbarui oleh aktivitas user. Request dengan header `X-Background-Request: 1`, aset statis, dan `/health` tidak memperpanjang sesi. Logout/timeout mencabut sesi di server sehingga salinan cookie lama tidak berlaku. "Ingat saya" **dihapus** karena bertentangan dengan timeout. Cart/data bisnis tidak tersentuh.
- **Pencarian**: `CatalogService.cari` (ILIKE terparameter) di nama, kategori, material, asal, era, kondisi, deskripsi. Yang cocok lebih banyak kata tampil lebih dulu, lalu bobot bidang. `/katalog/hasil?q=` mengembalikan kartu yang sama; filter, sortir, dan paginasi tetap di `catalog.js`.

## Pengujian
```
python -m pytest -q                       # 94 tes, SQLite in-memory
# PostgreSQL: plugin kecil yang mengganti URI TestingConfig, mis. PG_TEST_URL=postgresql+psycopg://user:pw@host/db_test
# JS katalog (jsdom): npm i jsdom; python tests/js/buat_fixture.py; node tests/js/uji_katalog.js
```
Config test mematikan CSRF; `test_csrf_menolak_perubahan_admin_tanpa_token` menyalakannya untuk membuktikan proteksi.

## Belum dikerjakan / keterbatasan
- **Keputusan: verifikasi email saja.** Google OAuth dan OTP telepon tidak diimplementasikan. Nomor telepon tetap tidak terverifikasi.
- Pengiriman email nyata belum teruji end-to-end (belum ada kredensial SMTP); hanya teruji lewat mock SMTP.
- Reset password mandiri belum ada. Registrasi masih membocorkan apakah email sudah terdaftar.
- Pencarian tidak mengabaikan aksen (tanpa `unaccent`) dan tanpa indeks trigram; cukup untuk katalog kecil.
- Konfirmasi di UI admin memakai `window.prompt`.
