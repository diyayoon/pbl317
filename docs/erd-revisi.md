# ERD Revisi — Albis Antique

## 1. Keputusan domain
Albis Antique diposisikan sebagai **e-commerce single-store**, bukan marketplace. Karena itu entitas `stores` dan role `seller` tidak diperlukan pada rancangan utama. Role inti cukup `admin` dan `customer`.

## 2. Entitas inti
- `users`: akun admin/customer, email unik, password hash, role, avatar, waktu pembuatan.
- `addresses`: alamat milik customer.
- `categories`: kategori koleksi barang antik.
- `products`: data utama produk, termasuk era, asal, material, kondisi, status autentikasi, harga, stok.
- `product_images`: beberapa gambar untuk satu produk; satu gambar dapat ditandai sebagai gambar utama.
- `carts`: keranjang aktif milik user.
- `cart_items`: item dan kuantitas di keranjang.
- `wishlists`: relasi user dengan produk yang disimpan.
- `orders`: header transaksi dan snapshot alamat pengiriman.
- `order_items`: snapshot produk, harga saat pembelian, dan kuantitas.
- `payments`: metode, status, bukti bayar, waktu pembayaran, dan approval admin.
- `reviews`: rating dan komentar setelah pembelian.

## 3. Relasi utama
```text
USERS 1 --- N ADDRESSES
USERS 1 --- 1 CARTS
CARTS 1 --- N CART_ITEMS
PRODUCTS 1 --- N CART_ITEMS

USERS N --- N PRODUCTS melalui WISHLISTS

USERS 1 --- N ORDERS
ORDERS 1 --- N ORDER_ITEMS
PRODUCTS 1 --- N ORDER_ITEMS
ORDERS 1 --- 1 PAYMENTS

CATEGORIES 1 --- N PRODUCTS
PRODUCTS 1 --- N PRODUCT_IMAGES
USERS 1 --- N REVIEWS
PRODUCTS 1 --- N REVIEWS
```

## 4. Atribut produk yang disarankan
```text
id
category_id
name
slug
description
price
stock
era
origin
material
condition
authenticity_status
created_at
updated_at
```

## 5. Catatan keamanan desain
Harga pada `order_items` harus menjadi snapshot yang dihitung server. Client tidak boleh menentukan total akhir. Semua operasi admin harus dilindungi role check. Akses order/address/review harus selalu diverifikasi kepemilikannya untuk mencegah IDOR.
