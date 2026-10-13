# Catatan perbaikan UI — 12 Oktober 2026

## Perbaikan pada versi ini

- Menonaktifkan maskot Elfaria sementara: runway di footer, script gerak, dan PNG pelari dihapus agar tidak membuat section tambahan yang mengganggu layout. Animasi dapat dirancang ulang nanti.
- Menambahkan `customer.dashboard` ke wrapper workspace bersama sehingga dashboard memakai satu sidebar customer, bukan sidebar inline duplikat.
- Menambahkan override responsif untuk posisi sidebar dan konten dashboard customer/admin.
- Merapikan alignment ikon link header agar SVG/ikon tepat di tengah tombol bulat.
- Mengubah flash server dan toast interaksi menjadi notifikasi ringkas di kanan atas; flash server menutup otomatis setelah sekitar 5 detik.
- Menampilkan seluruh 8 produk katalog per halaman. Sebelumnya pagination 4 produk membuat grid berubah dari dua baris menjadi satu setelah JavaScript berjalan.
- Memperlambat jeda slider hero dari 6,5 menjadi 8,5 detik.

## Pemeriksaan yang dilakukan

- 23 file Python lolos pemeriksaan kompilasi sintaks.
- 22 template HTML/Jinja lolos pemeriksaan parsing.
- 9 file JavaScript lolos `node --check`.
- Referensi template ke runway/script Elfaria tidak ditemukan.

## Batasan

Belum dilakukan pengujian browser end-to-end pada seluruh halaman dan ukuran layar. Jalankan proyek secara lokal dan verifikasi beranda, katalog, detail produk, login/register, dashboard customer, dan admin pada desktop serta mobile.
