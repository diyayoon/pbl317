# Albis Antique — UI Interaction Polish

Perubahan ini berfokus pada pengalaman visual dan mempertahankan identitas light-blue icy, ornamen monarki, serta struktur Flask yang sudah ada.

## Perubahan
- Hero carousel berjalan otomatis setiap 6,5 detik; tombol play/pause dihilangkan.
- Konten hero (foto, nama, dan deskripsi singkat) mengarah ke katalog; harga dan tautan detail di hero dihilangkan.
- Animasi kilau dibatasi dalam showcase dan menyesuaikan ukuran layar.
- Lingkaran dekoratif yang menutupi foto produk dihapus.
- Placeholder thumbnail yang tidak berisi foto nyata disembunyikan.
- Foto detail produk dapat dibuka dalam lightbox dan ditutup dengan tombol close atau Escape.
- Tombol favorit memberi feedback visual; tombol tambah keranjang memberi feedback dan toast.
- Aksi cepat kartu tetap terlihat dan bisa diakses pada perangkat sentuh/keyboard.
- Fokus keyboard, active state, toast, dan reduced-motion styling dirapikan.

## Catatan pengujian
- JavaScript diperiksa dengan `node --check`.
- File Python lolos `compileall`.
- Template Jinja berhasil diparse.
- `pytest` belum bisa dijalankan di lingkungan audit ini karena dependensi Flask tidak terpasang (`ModuleNotFoundError: flask`). Jalankan tes di virtual environment project setelah dependensi diinstal.
