# Rancangan OOP — Albis Antique

OOP diterapkan ketika memang membantu domain, bukan sekadar membuat setiap tabel menjadi class turunan yang tidak diperlukan.

## Enkapsulasi
`Pengguna.set_password()` dan `Pengguna.cek_password()` mengatur password hash. Nilai hash tidak dikeluarkan melalui serializer publik. `Produk.ubah_stok()` memvalidasi stok agar tidak negatif.

## Pewarisan
`Pengguna` menjadi kelas dasar perilaku akun. `Customer` dan `Admin` dapat menurunkan perilaku umum, misalnya identitas dan tujuan dashboard. Untuk model SQLAlchemy, implementasi final dapat menggunakan single-table inheritance atau komposisi role sesuai kebutuhan; jangan memaksakan inheritance bila membuat schema lebih rumit.

## Polimorfisme
Method `halaman_awal()` dapat menghasilkan endpoint berbeda:
- Customer → `customer.dashboard`
- Admin → `admin.dashboard`

Interface pembayaran juga dapat memiliki method `proses()` yang sama dengan implementasi berbeda untuk Transfer Bank dan QRIS.

## Abstraksi
`LayananPembayaran` atau `MetodePembayaran` dapat menggunakan `ABC` dan `@abstractmethod`. Detail integrasi payment gateway disembunyikan dari route sehingga route hanya memanggil service yang konsisten.

## OOP frontend
Versi UI ini juga memisahkan perilaku ke class:
- `PengelolaBahasa`
- `EfekSalju`
- `FilterKatalog`
- `KeranjangPrototype`

Keranjang `localStorage` hanya untuk prototype UI dan harus diganti session/database ketika backend checkout dibuat.
