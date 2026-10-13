# Akun Demo Lokal Albis Antique

Mode ini hanya untuk mencoba UI sebelum integrasi PostgreSQL. Akun tidak tersimpan ke database dan bukan untuk production.

## Akun

- Customer: `customer@albis.local` / `AlbisCustomer123!`
- Admin: `admin@albis.local` / `AlbisAdmin123!`

## Cara pakai

1. Jalankan aplikasi seperti biasa (`python run.py`).
2. Buka `/login`, masukkan email dan password akun demo.
3. Customer diarahkan ke `/customer/akun`; admin diarahkan ke `/admin/`.
4. Gunakan tombol **Keluar** di navbar untuk berganti akun.

Mode demo aktif secara default untuk konfigurasi development. Untuk mematikannya, set `DEMO_AUTH_ENABLED=0` pada `.env`. Sebelum deploy atau mengintegrasikan autentikasi PostgreSQL, nonaktifkan dan ganti mekanisme ini dengan model pengguna persisten serta password hash.

Keranjang, wishlist, profil, pesanan, dan data dashboard masih berupa halaman prototipe. Login demo hanya mengaktifkan sesi dan pembatasan akses berbasis role; tidak membuat data tersimpan permanen.
