# Registrasi, verifikasi email, dan Midtrans

## Alur registrasi
Daftar (email, nama lengkap, password, konfirmasi) -> halaman "Registrasi berhasil, cek email" -> masukkan kode 6 digit
(atau klik tautan di email) -> login. Alamat dan nomor telepon dilengkapi setelah login (Profil / Alamat).
Aksi pesan, unggah bukti, ulasan, dan bayar online butuh email terverifikasi (dicek di backend).
Ganti password mandiri: `/customer/keamanan` (password lama wajib, sesi di perangkat lain dikeluarkan).

## Docker
Pastikan variabel `MAIL_*`, `APP_BASE_URL`, `MIDTRANS_*` ada di `environment:` compose (sudah ditambahkan) dan container dibuat ulang.

## Cek email tidak terkirim
`flask --app run uji-email alamat@tujuan.com` memeriksa konfigurasi dan mencoba kirim; hasilnya menyebut jenis error
(535 = App Password salah/2-Step belum aktif, gaierror = tidak ada internet), tanpa menampilkan password.

## Midtrans (Snap Redirect)
Uji kunci dan koneksi lebih dulu: `python -m flask --app run uji-midtrans` (hanya ke sandbox; membuat satu transaksi uji tanpa uang).
1. Daftar akun sandbox Midtrans, ambil Server Key (dashboard dalam mode Sandbox), isi `MIDTRANS_SERVER_KEY` di `.env`.
2. Isi `APP_BASE_URL` dengan alamat aplikasi yang dibuka di browser (mis. http://localhost:5000).
3. Jalankan migration: `python -m flask --app run db upgrade` (revisi 0008, backup dulu).
4. Checkout -> pilih "Bayar Online (Midtrans)" -> di halaman Pesanan klik "Bayar sekarang" -> halaman Midtrans -> bayar
   lewat simulator sandbox -> kembali ke Pesanan; status disinkronkan otomatis lewat Status API (tanpa webhook).
5. Webhook (opsional, butuh alamat publik, mis. ngrok/domain): isi Payment Notification URL di dashboard Midtrans dengan
   `APP_BASE_URL/midtrans/notifikasi`. Endpoint memverifikasi signature SHA512 lalu mengambil status resmi dari Midtrans.

Keamanan: kunci server hanya di environment, signature diverifikasi constant-time, status diambil ulang dari Midtrans,
jumlah dicocokkan dengan total pesanan, notifikasi idempoten dan tidak menurunkan status lunas.
Belum teruji end-to-end ke sandbox Midtrans (tidak ada akses jaringan saat pengembangan); seluruh test memakai mock.
Refund/chargeback hanya dicatat, belum mengubah status pesanan. Pembayaran yang masuk setelah pesanan dibatalkan
ditandai di catatan pembayaran agar admin menanganinya manual.

## Webhook (notifikasi otomatis) di localhost
Midtrans harus bisa menjangkau alamat tokomu dari internet, jadi di komputer sendiri perlu terowongan (ngrok atau cloudflared).
1. Jalankan aplikasi, lalu buka terowongan ke portnya (mis. `ngrok http 5000`). Salin alamat `https://xxxx.ngrok...`.
2. Isi `.env`: `APP_BASE_URL=https://xxxx.ngrok...` (alamat yang sama dengan yang kamu buka di browser). Karena HTTPS,
   `SESSION_COOKIE_SECURE=1` boleh dipakai. Buat ulang container/restart aplikasi.
3. Dashboard Midtrans (mode Sandbox): SETTINGS > CONFIGURATION > **Payment Notification URL** =
   `https://xxxx.ngrok.../midtrans/notifikasi`, lalu simpan.
4. Buat pesanan "Bayar Online", bayar lewat simulator sandbox. Cek log aplikasi: `Notifikasi Midtrans diproses (lunas)`
   dan pesanan berubah ke Diproses (juga tercatat di audit log: `midtrans_lunas`).
Alamat gratis ngrok bisa berganti saat dijalankan ulang; kalau berganti, ubah `APP_BASE_URL` dan Payment Notification URL.

Perilaku endpoint: signature SHA-512 diverifikasi, lalu status resmi diambil ulang dari Midtrans; 403 bila signature salah,
404 bila pesanan tidak dikenal, 400 bila jumlah tidak cocok, 5xx bila Midtrans tidak terjangkau (Midtrans akan mengulang kirim).
Notifikasi ganda atau terlambat aman. Notifikasi palsu yang tidak sesuai status resmi tidak mengubah apa pun.

