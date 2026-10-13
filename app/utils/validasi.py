"""Validasi input dari browser. Browser tidak boleh dipercaya, jadi aturan ini WAJIB di server."""

import re
from datetime import date

# ===== POLA YANG DIPAKAI BERSAMA =====
POLA_USERNAME = re.compile(r'^[A-Za-z0-9_.]{3,30}$')
HURUF_NAMA_TAMBAHAN = " .'-"  # selain huruf, nama boleh berisi spasi, titik, apostrof, tanda hubung
POLA_TELEPON = re.compile(r'^62\d{8,13}$')


# BAGIAN : Validasi › Registrasi
# FUNGSI : Memeriksa dan merapikan 6 kolom form register; mengembalikan (nilai_bersih, galat).
class ValidasiRegistrasi:
    # BAGIAN : Validasi › Registrasi › Konstruktor
    # FUNGSI : Menyimpan data form mentah (request.form) dan menyiapkan wadah hasil.
    def __init__(self, data):
        self.data = data
        self.nilai = {}
        self.galat = {}

    # BAGIAN : Validasi › Registrasi › Utilitas
    # FUNGSI : Mengambil satu kolom sebagai teks (kosong jika tidak ada), tanpa spasi tepi.
    def _ambil(self, nama, rapikan=True):
        mentah = self.data.get(nama, '')
        mentah = mentah if isinstance(mentah, str) else ''
        return mentah.strip() if rapikan else mentah

    # BAGIAN : Validasi › Registrasi › Username
    # FUNGSI : 3-30 karakter: huruf, angka, titik, garis bawah.
    def _username(self):
        nilai = self._ambil('username')
        if not nilai:
            self.galat['username'] = 'Username tidak boleh kosong.'
        elif len(nilai) < 3:
            self.galat['username'] = 'Username minimal 3 karakter.'
        elif not POLA_USERNAME.match(nilai):
            self.galat['username'] = 'Username hanya boleh huruf, angka, titik, dan garis bawah (maksimal 30 karakter).'
        self.nilai['username'] = nilai

    # BAGIAN : Validasi › Registrasi › Password
    # FUNGSI : Hanya panjang: 16-128 karakter, tanpa paksaan huruf besar/simbol. Tidak disimpan di nilai.
    def _password(self):
        sandi = self._ambil('password', rapikan=False)
        if not sandi.strip():
            self.galat['password'] = 'Password tidak boleh kosong.'
        elif len(sandi) < 16:
            self.galat['password'] = 'Password minimal 16 karakter.'
        elif len(sandi) > 128:
            self.galat['password'] = 'Password maksimal 128 karakter.'

    # BAGIAN : Validasi › Registrasi › Nama
    # FUNGSI : 2-100 karakter, hanya huruf, spasi, titik, apostrof, tanda hubung.
    def _nama(self):
        nilai = re.sub(r'\s+', ' ', self._ambil('nama'))
        if not nilai:
            self.galat['nama'] = 'Nama tidak boleh kosong.'
        elif len(nilai) < 2:
            self.galat['nama'] = 'Nama minimal 2 karakter.'
        elif len(nilai) > 100 or not self._nama_valid(nilai):
            self.galat['nama'] = 'Nama hanya boleh berisi huruf, spasi, titik, apostrof, dan tanda hubung.'
        self.nilai['nama'] = nilai

    # BAGIAN : Validasi › Registrasi › Nama
    # FUNGSI : Huruf pertama harus huruf (termasuk huruf beraksen); sisanya huruf atau tanda yang diizinkan.
    @staticmethod
    def _nama_valid(teks):
        return teks[0].isalpha() and all(c.isalpha() or c in HURUF_NAMA_TAMBAHAN for c in teks)

    # BAGIAN : Validasi › Registrasi › Tanggal lahir
    # FUNGSI : Format YYYY-MM-DD, tidak di masa depan, tidak lebih dari 120 tahun lalu.
    def _tanggal_lahir(self):
        teks = self._ambil('tanggal_lahir')
        self.nilai['tanggal_lahir'] = teks
        if not teks:
            self.galat['tanggal_lahir'] = 'Tanggal lahir tidak boleh kosong.'
            return
        try:
            lahir = date.fromisoformat(teks)
        except ValueError:
            self.galat['tanggal_lahir'] = 'Format tanggal lahir tidak valid.'
            return
        hari_ini = date.today()
        try:
            batas = hari_ini.replace(year=hari_ini.year - 120)
        except ValueError:  # 29 Februari
            batas = hari_ini.replace(year=hari_ini.year - 120, day=28)
        if lahir > hari_ini:
            self.galat['tanggal_lahir'] = 'Tanggal lahir tidak boleh di masa depan.'
        elif lahir < batas:
            self.galat['tanggal_lahir'] = 'Tanggal lahir tidak valid (lebih dari 120 tahun lalu).'

    # BAGIAN : Validasi › Registrasi › Alamat
    # FUNGSI : 10-255 karakter.
    def _alamat(self):
        nilai = re.sub(r'[ \t]+', ' ', self._ambil('alamat'))
        if not nilai:
            self.galat['alamat'] = 'Alamat tidak boleh kosong.'
        elif len(nilai) < 10:
            self.galat['alamat'] = 'Alamat terlalu singkat, tuliskan minimal 10 karakter.'
        elif len(nilai) > 255:
            self.galat['alamat'] = 'Alamat maksimal 255 karakter.'
        self.nilai['alamat'] = nilai

    # BAGIAN : Validasi › Registrasi › Telepon
    # FUNGSI : Merapikan (08xx / +62xx jadi 62xx) lalu mewajibkan awalan 62 dan 10-15 angka.
    def _telepon(self):
        nilai = self.normalisasi_telepon(self._ambil('telepon'))
        if not nilai:
            self.galat['telepon'] = 'Nomor telepon tidak boleh kosong.'
        elif not POLA_TELEPON.match(nilai):
            self.galat['telepon'] = 'Nomor telepon harus diawali 62 dan berisi 10-15 angka.'
        self.nilai['telepon'] = nilai

    # BAGIAN : Validasi › Registrasi › Telepon
    # FUNGSI : Membuang spasi/tanda baca, mengganti awalan 0 atau +62 menjadi 62.
    @staticmethod
    def normalisasi_telepon(teks):
        angka = re.sub(r'[^\d+]', '', teks)
        angka = angka[1:] if angka.startswith('+') else angka
        angka = angka.replace('+', '')
        if angka.startswith('0'):
            angka = '62' + angka[1:]
        return angka

    # BAGIAN : Validasi › Registrasi › Jalankan
    # FUNGSI : Menjalankan semua aturan berurutan (username dulu karena dipakai aturan password).
    def periksa(self):
        self._username()
        self._password()
        self._nama()
        self._tanggal_lahir()
        self._alamat()
        self._telepon()
        return self.nilai, self.galat
