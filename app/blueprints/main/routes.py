"""Route publik Albis Antique.

Tahap saat ini menggunakan data dummy agar antarmuka dapat diuji tanpa database.
Ketika PostgreSQL diaktifkan, sumber data di file ini dapat diganti dengan query model/service.
"""

from flask import abort, render_template, request
from . import main_bp

# ===== DATA DUMMY: KATEGORI =====
KATEGORI = [
    {'slug': 'timepiece', 'nama': 'Jam & Timepiece', 'ikon': '⌚', 'jumlah': 18},
    {'slug': 'camera', 'nama': 'Kamera Vintage', 'ikon': '📷', 'jumlah': 12},
    {'slug': 'porcelain', 'nama': 'Porselen & Keramik', 'ikon': '🏺', 'jumlah': 21},
    {'slug': 'books', 'nama': 'Buku & Manuskrip', 'ikon': '📚', 'jumlah': 16},
    {'slug': 'jewelry', 'nama': 'Perhiasan Antik', 'ikon': '💍', 'jumlah': 14},
    {'slug': 'music', 'nama': 'Musik Vintage', 'ikon': '🎼', 'jumlah': 9},
    {'slug': 'decor', 'nama': 'Dekorasi & Interior', 'ikon': '🪞', 'jumlah': 20},
    {'slug': 'travel', 'nama': 'Travel Collectibles', 'ikon': '🧭', 'jumlah': 10},
]

# ===== DATA DUMMY: PRODUK =====
PRODUK = [
    {
        'id': 1,
        'nama': 'Brass Pocket Watch',
        'kategori': 'Jam & Timepiece',
        'slug_kategori': 'timepiece',
        'era': '1900–1949',
        'asal': 'France',
        'kondisi': 'Good',
        'material': 'Brass',
        'harga': 1850000,
        'stok': 1,
        'rating': 4.9,
        'ulasan': 18,
        'autentikasi': 'Verified',
        'deskripsi': 'Jam saku bergaya Art Deco dengan karakter patina alami dan detail mekanis klasik.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Pocket%20watch%20MET%20SF1979%20498%201%20img1.jpg',
        'alt_gambar': 'Foto Brass Pocket Watch',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Pocket_watch_MET_SF1979_498_1_img1.jpg',
    },
    {
        'id': 2,
        'nama': 'Kodak Folding Camera',
        'kategori': 'Kamera Vintage',
        'slug_kategori': 'camera',
        'era': '1900–1949',
        'asal': 'USA',
        'kondisi': 'Fair',
        'material': 'Metal & Leather',
        'harga': 2400000,
        'stok': 1,
        'rating': 4.7,
        'ulasan': 12,
        'autentikasi': 'Documented',
        'deskripsi': 'Kamera lipat vintage dengan konstruksi metal dan leather bellows untuk kolektor fotografi analog.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Kokak%20Pocket%2C%201896%20-%20Mus%C3%A9e%20Nic%C3%A9phore%20Ni%C3%A9pce%20-%20DSC06071.JPG',
        'alt_gambar': 'Foto Kodak Folding Camera',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Kokak_Pocket,_1896_-_Musée_Nicéphore_Niépce_-_DSC06071.JPG',
    },
    {
        'id': 3,
        'nama': 'Blue Porcelain Vase',
        'kategori': 'Porselen & Keramik',
        'slug_kategori': 'porcelain',
        'era': '1950–1999',
        'asal': 'Japan',
        'kondisi': 'Excellent',
        'material': 'Porcelain',
        'harga': 1325000,
        'stok': 1,
        'rating': 4.8,
        'ulasan': 24,
        'autentikasi': 'Verified',
        'deskripsi': 'Vas porselen bernuansa biru-putih dengan motif klasik dan glasir yang masih terjaga.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Blue%20and%20white%20vase%201271%201368%20Jingdezhen%20unearthed%20in%20Jiangxi%20Province.jpg',
        'alt_gambar': 'Foto Blue Porcelain Vase',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Blue_and_white_vase_1271_1368_Jingdezhen_unearthed_in_Jiangxi_Province.jpg',
    },
    {
        'id': 4,
        'nama': 'Victorian Cameo Brooch',
        'kategori': 'Perhiasan Antik',
        'slug_kategori': 'jewelry',
        'era': '1800s',
        'asal': 'England',
        'kondisi': 'Good',
        'material': 'Silver',
        'harga': 2750000,
        'stok': 1,
        'rating': 4.9,
        'ulasan': 31,
        'autentikasi': 'Verified',
        'deskripsi': 'Bros cameo dengan siluet klasik, frame berornamen, dan karakter Victorian yang kuat.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Firm%20of%20Fortunato%20Pio%20Castellani%20-%20Brooch%20with%20Cameo%20Bust%20of%20Ellen%20Walters%20-%20Walters%20572001.jpg',
        'alt_gambar': 'Foto Victorian Cameo Brooch',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Firm_of_Fortunato_Pio_Castellani_-_Brooch_with_Cameo_Bust_of_Ellen_Walters_-_Walters_572001.jpg',
    },
    {
        'id': 5,
        'nama': 'Leather Bound Journal',
        'kategori': 'Buku & Manuskrip',
        'slug_kategori': 'books',
        'era': '1900–1949',
        'asal': 'Italy',
        'kondisi': 'Fair',
        'material': 'Leather & Paper',
        'harga': 980000,
        'stok': 1,
        'rating': 4.6,
        'ulasan': 9,
        'autentikasi': 'Documented',
        'deskripsi': 'Jurnal lama berkulit dengan detail emboss dan halaman berpatina yang menampilkan usia alaminya.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Jfisher%20journal%2018160712.jpg',
        'alt_gambar': 'Foto Leather Bound Journal',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Jfisher_journal_18160712.jpg',
    },
    {
        'id': 6,
        'nama': 'Brass Telescope',
        'kategori': 'Travel Collectibles',
        'slug_kategori': 'travel',
        'era': '1950–1999',
        'asal': 'Germany',
        'kondisi': 'Good',
        'material': 'Brass & Glass',
        'harga': 2100000,
        'stok': 2,
        'rating': 4.7,
        'ulasan': 14,
        'autentikasi': 'Inspected',
        'deskripsi': 'Teleskop kuningan bergaya nautikal dengan optik dekoratif, ideal untuk display dan koleksi.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Newton%20telescope%20replica%201668.jpg',
        'alt_gambar': 'Foto Brass Telescope',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Newton_telescope_replica_1668.jpg',
    },
    {
        'id': 7,
        'nama': 'Vintage Music Box',
        'kategori': 'Musik Vintage',
        'slug_kategori': 'music',
        'era': '1950–1999',
        'asal': 'Switzerland',
        'kondisi': 'Excellent',
        'material': 'Wood & Metal',
        'harga': 1675000,
        'stok': 1,
        'rating': 4.8,
        'ulasan': 20,
        'autentikasi': 'Verified',
        'deskripsi': 'Kotak musik mekanik vintage dengan ukiran lembut dan karakter suara yang hangat.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Music%20Box%20And%20Key%2C%20late%2019th%20century%20%28CH%2018416829-2%29.jpg',
        'alt_gambar': 'Foto Vintage Music Box',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Music_Box_And_Key,_late_19th_century_(CH_18416829-2).jpg',
    },
    {
        'id': 8,
        'nama': 'Ornamental Hand Mirror',
        'kategori': 'Dekorasi & Interior',
        'slug_kategori': 'decor',
        'era': '1900–1949',
        'asal': 'France',
        'kondisi': 'Good',
        'material': 'Silver & Glass',
        'harga': 1450000,
        'stok': 1,
        'rating': 4.5,
        'ulasan': 11,
        'autentikasi': 'Inspected',
        'deskripsi': 'Cermin tangan ornamental dengan frame perak klasik dan detail ukiran yang halus.',
        'gambar': 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Hand%20Mirror%2C%20ca.%201890%20%28CH%2018660743%29.jpg',
        'alt_gambar': 'Foto Ornamental Hand Mirror',
        'sumber_gambar': 'https://commons.wikimedia.org/wiki/File:Hand_Mirror,_ca._1890_(CH_18660743).jpg',
    },
]


# ===== FOTO KATEGORI: MEMAKAI FOTO PRODUK PERTAMA DI KATEGORI TERSEBUT =====
for kategori in KATEGORI:
    produk_kategori = next((item for item in PRODUK if item['slug_kategori'] == kategori['slug']), None)
    kategori['gambar'] = produk_kategori['gambar'] if produk_kategori else ''


# ===== ROUTE: BERANDA =====
@main_bp.get('/')
def beranda():
    """Menampilkan halaman beranda beserta kategori dan produk pilihan."""
    return render_template(
        'main/index.html',
        kategori_unggulan=KATEGORI,
        produk_unggulan=PRODUK[:4],
        produk_slide=PRODUK[:6],
        produk_terbaru=PRODUK[4:8],
    )


# ===== ROUTE: KATALOG =====
@main_bp.get('/katalog')
def katalog():
    """Menampilkan katalog. Filter utama masih berjalan di frontend untuk tahap prototipe."""
    kategori_awal = request.args.get('kategori', '')
    return render_template(
        'main/explore.html',
        kategori_unggulan=KATEGORI,
        produk=PRODUK,
        kategori_awal=kategori_awal,
    )


# ===== ROUTE: DETAIL PRODUK =====
@main_bp.get('/produk/<int:produk_id>')
def detail_produk(produk_id):
    """Menampilkan detail satu produk dan beberapa produk terkait."""
    produk = next((item for item in PRODUK if item['id'] == produk_id), None)
    if not produk:
        abort(404)

    produk_terkait = [item for item in PRODUK if item['id'] != produk_id][:4]
    return render_template('main/product.html', produk=produk, produk_terkait=produk_terkait)
