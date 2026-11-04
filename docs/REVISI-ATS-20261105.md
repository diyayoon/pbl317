# Revisi ATS Albis Antique — 5 November 2026

Dokumen ini menjelaskan fitur yang direalisasikan pada revisi ini dan langkah penerapannya. Perubahan dibuat pada source code; database deployment tidak termasuk dalam ZIP dan tidak diubah otomatis.

## 1. Peran akun

- Registrasi publik `/auth/register` selalu membuat `role="customer"`. Form tidak menerima atau mempercayai nilai role dari browser.
- Akun admin dibuat dari server melalui `flask --app run create-admin`. Password diminta secara interaktif, tidak ditulis pada command history, minimal 16 karakter, dan disimpan menggunakan password hashing Werkzeug.
- Halaman `/admin/pengguna` menampilkan dua bagian: daftar customer yang bisa dikelola dan daftar admin read-only. Endpoint daftar admin hanya `GET`; tidak ada endpoint panel untuk mengubah atau menghapus admin lain.
- Admin biasa hanya dapat mengelola akun customer. Pengelolaan administrator memerlukan akses server.

## 2. Permintaan refund Midtrans

Alur yang tersedia:

1. Customer dapat mengajukan refund untuk pesanan miliknya yang berstatus `Diproses`, telah dibayar melalui Midtrans, dan belum dikirim.
2. Backend mengambil status transaksi langsung dari Midtrans, memeriksa nilai pembayaran, metode pembayaran, dan status gateway. Browser tidak menentukan nominal refund.
3. Permintaan disimpan di `refund_requests` sebagai `Menunggu persetujuan`.
4. Admin dapat menyetujui atau menolak permintaan melalui `/admin/refund`.
5. Persetujuan admin mengirim refund request ke Midtrans. Status lokal tetap `Diproses` sampai GET Status API memberikan konfirmasi final.
6. Refund hanya menjadi `Berhasil` setelah `bank_confirmed_at` ditemukan pada detail refund yang memiliki `refund_key` sama dan nominalnya cocok dengan jumlah penuh yang diminta. Pembatalan transaksi Capture kartu kredit ditangani melalui Cancel API.
7. Setelah konfirmasi final, pesanan dan pembayaran ditandai `Direfund` (atau `Dibatalkan` untuk cancel), dan stok dikembalikan satu kali.
8. Pesanan tidak bisa dipindahkan ke `Dikirim` selama refund masih menunggu keputusan, diproses, atau gagal dan belum ditangani.

Metode yang diizinkan mengikuti dukungan endpoint refund Midtrans: `credit_card`, `gopay`, `shopeepay`, `dana`, `ovo`, `qris`, `kredivo`, dan `akulaku`. Capture kartu kredit yang belum settlement menggunakan Cancel API. Metode lain akan diberi penjelasan agar customer menghubungi admin untuk penanganan manual. Lihat dokumentasi resmi:
- https://docs.midtrans.com/reference/refund-transaction
- https://docs.midtrans.com/reference/get-transaction-status

**Catatan operasional:** sandbox tidak selalu mensimulasikan alur refund dan konfirmasi bank seperti transaksi produksi. Uji endpoint menggunakan mock/test dan lakukan validasi dashboard sandbox sesuai metode yang tersedia. Jangan menganggap respons awal POST sebagai bukti dana telah kembali.

## 3. Laporan penjualan dan ekspor

- Admin membuka `/admin/laporan`.
- Filter periode menggunakan `tanggal_awal` dan `tanggal_akhir`, format `YYYY-MM-DD`, berdasarkan zona waktu `Asia/Jakarta` (WIB).
- Pendapatan, pesanan selesai, dan jumlah produk terjual hanya menghitung pesanan `Selesai`. Pesanan dibatalkan atau direfund tidak dihitung sebagai pendapatan penjualan selesai.
- `GET /admin/laporan/export.pdf` menghasilkan PDF.
- `GET /admin/laporan/export.xlsx` menghasilkan Excel.
- Kedua endpoint dilindungi `@admin_required` dan menggunakan filter tanggal yang sama dengan halaman laporan.

## 4. Perbaikan integrasi dan tampilan

- Route dashboard admin `/admin/` ditambahkan kembali karena template dan tautannya sudah ada tetapi route belum terdaftar pada source ZIP.
- Halaman daftar pengguna memuat `admin.js` agar data customer dan daftar admin read-only diambil dari API/database, bukan hanya teks HTML.
- Login dan register memakai identitas brand yang konsisten; validasi browser dasar login diaktifkan.
- Favicon tersedia dalam ICO, PNG 16, 32, 96, 192, dan Apple Touch Icon 180 px. File ikon lama yang digunakan pada path `icon-albis.png` dioptimalkan agar lebih ringan.
- Statistik koleksi/kategori di beranda berasal dari data database, bukan angka statis.
- Logo navbar mobile mengikuti ukuran wadahnya.
- Gambar hero mempunyai fallback lokal jika sumber gambar utama gagal dimuat.
- `TestingConfig` mematikan kredensial Midtrans/SMTP dan menetapkan ongkir test secara eksplisit, sehingga pytest tidak menggunakan layanan eksternal atau nilai `.env` development.
- Halaman admin pembayaran dapat dibuka langsung; audit login admin memiliki label aksi tersendiri.

## 5. Migration database

Revisi ini menambahkan migration `20261105_0010` untuk tabel `refund_requests`, dengan parent migration `20261027_0009`.

**Sebelum migration:**
1. Backup PostgreSQL.
2. Deploy/build source code baru sehingga image aplikasi sudah memuat migration ini.
3. Jalankan migration satu kali dengan akun pemilik skema (`MIGRATION_DATABASE_URL`).
4. Periksa `flask db current` dan `flask db heads`; keduanya seharusnya menunjukkan `20261105_0010`.

Contoh setelah image baru tersedia (sesuaikan nama image, file Compose, dan environment dengan deployment):

```bash
python -m flask --app run db upgrade
python -m flask --app run db current
python -m flask --app run db heads
```

Jangan jalankan migration sebelum image baru yang berisi migration `20261105_0010` tersedia. Jangan menghapus volume database. Migration ini menambahkan tabel baru dan tidak menghapus tabel pesanan/pembayaran yang sudah ada.

## 6. Pengujian

Jalankan pada virtual environment project:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Pengujian memakai SQLite in-memory melalui `TestingConfig`; PostgreSQL dan Docker tidak perlu dinyalakan untuk test tersebut. Tes Midtrans memakai mock untuk menghindari transaksi nyata. Tambahan test pada revisi ini meliputi:
- pemisahan daftar customer dan admin read-only;
- daftar admin tidak memiliki method mutasi;
- filter laporan serta ekspor PDF/Excel;
- pengajuan, penolakan, persetujuan, sinkronisasi refund;
- nominal refund parsial tidak boleh dianggap refund penuh;
- pesanan tidak dapat dikirim selama permintaan refund belum selesai;
- CLI `create-admin` dan audit login admin.

Setelah pytest, lakukan juga pemeriksaan manual: register customer, login sebagai admin yang dibuat melalui CLI, CRUD produk, checkout sandbox, refund (sesuai kemampuan sandbox), filter tanggal laporan, unduh PDF/Excel, serta akses dari browser melalui Tailscale.

## 7. Dependensi baru

`requirements.txt` menambahkan:
- `openpyxl==3.1.5` untuk ekspor Excel.
- `reportlab==4.4.9` untuk ekspor PDF.

Install ulang dependensi atau rebuild image agar kedua paket tersedia.

## 8. Kredensial dan file lokal

ZIP revisi tidak menyertakan `.env`, `.git`, `.venv`, file database lokal, atau direktori upload. Salin `.env.example` menjadi `.env` hanya pada environment lokal/server dan isi rahasia secara privat. Jika kredensial pernah dibagikan melalui chat, log, atau repository publik, rotasi sebelum demo.

## 9. Hasil verifikasi source revisi

- `python -m compileall -q app migrations tests`: lulus.
- `node --check` untuk `main.js`, `admin.js`, dan `orders.js`: lulus.
- Semua template Jinja: berhasil diparse.
- 157 test terkumpul. Seluruh modul test dijalankan per kelompok dan total 157 test lulus. Satu kali percobaan menjalankan semua test dalam satu proses melewati batas waktu pemeriksaan 6 menit; jalankan ulang `python -m pytest -v` di environment development project untuk verifikasi akhir lokal.
- Tes Midtrans menggunakan mock; transaksi refund live dan konfirmasi bank tidak dilakukan dari pemeriksaan ini.


## Penyempurnaan UI dan ulasan per pembelian

- Pratinjau gambar upload produk dan kategori diizinkan oleh Content Security Policy melalui sumber `blob:`.
- Menu aksi pengguna menggunakan panel overlay fixed agar tidak memperlebar atau mengubah tinggi tabel.
- Tombol export laporan dirapikan ke sisi kanan; workbook Excel menggunakan Excel Table, lebar kolom terukur, dan tanpa freeze pane.
- Logo brand di form login dan registrasi dihapus.
- Ulasan diikat ke `order_item_id`: satu ulasan untuk setiap item pembelian selesai, sehingga pembelian produk yang sama pada pesanan lain tetap dapat diulas.
- Migration baru: `20261105_0011_reviews_per_purchase`. Ulasan lama dipertahankan dan dikaitkan ke satu item pesanan selesai bila tersedia.
