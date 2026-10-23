"""Validasi server untuk data registrasi; selaras dengan skema tabel users."""
import re

POLA_EMAIL = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
POLA_TELEPON = re.compile(r'^62\d{8,13}$')
HURUF_NAMA_TAMBAHAN = " .'-"


class ValidasiRegistrasi:
    """Memeriksa kolom email, password, nama, alamat, dan nomor telepon."""
    def __init__(self, data):
        self.data = data
        self.nilai = {}
        self.galat = {}

    def _ambil(self, nama, rapikan=True):
        mentah = self.data.get(nama, '')
        mentah = mentah if isinstance(mentah, str) else ''
        return mentah.strip() if rapikan else mentah

    def _email(self):
        nilai = self._ambil('email').lower()
        if not nilai:
            self.galat['email'] = 'Email tidak boleh kosong.'
        elif len(nilai) > 254 or not POLA_EMAIL.fullmatch(nilai):
            self.galat['email'] = 'Format email tidak valid.'
        self.nilai['email'] = nilai

    def _password(self):
        sandi = self._ambil('password', rapikan=False)
        konfirmasi = self._ambil('konfirmasi_password', rapikan=False)
        if not sandi.strip():
            self.galat['password'] = 'Kata sandi tidak boleh kosong.'
        elif len(sandi) < 16:
            self.galat['password'] = 'Kata sandi minimal 16 karakter.'
        elif len(sandi) > 128:
            self.galat['password'] = 'Kata sandi maksimal 128 karakter.'
        if not konfirmasi:
            self.galat['konfirmasi_password'] = 'Konfirmasi kata sandi wajib diisi.'
        elif sandi != konfirmasi:
            self.galat['konfirmasi_password'] = 'Konfirmasi kata sandi tidak cocok.'

    @staticmethod
    def _nama_valid(teks):
        return bool(teks) and teks[0].isalpha() and all(c.isalpha() or c in HURUF_NAMA_TAMBAHAN for c in teks)

    def _nama(self):
        nilai = re.sub(r'\s+', ' ', self._ambil('nama'))
        if not nilai:
            self.galat['nama'] = 'Nama lengkap tidak boleh kosong.'
        elif len(nilai) < 3:
            self.galat['nama'] = 'Nama lengkap minimal 3 karakter.'
        elif len(nilai) > 100 or not self._nama_valid(nilai):
            self.galat['nama'] = 'Nama hanya boleh berisi huruf, spasi, titik, apostrof, dan tanda hubung.'
        self.nilai['nama'] = nilai

    def _alamat(self):
        nilai = re.sub(r'[ \t]+', ' ', self._ambil('alamat'))
        if not nilai:
            self.galat['alamat'] = 'Alamat tidak boleh kosong.'
        elif len(nilai) < 10:
            self.galat['alamat'] = 'Alamat terlalu singkat; tuliskan minimal 10 karakter.'
        elif len(nilai) > 255:
            self.galat['alamat'] = 'Alamat maksimal 255 karakter.'
        self.nilai['alamat'] = nilai

    @staticmethod
    def normalisasi_telepon(teks):
        angka = re.sub(r'[^\d+]', '', teks)
        angka = angka[1:] if angka.startswith('+') else angka
        angka = angka.replace('+', '')
        if angka.startswith('0'):
            angka = '62' + angka[1:]
        return angka

    def _telepon(self):
        nilai = self.normalisasi_telepon(self._ambil('telepon'))
        if not nilai:
            self.galat['telepon'] = 'Nomor telepon tidak boleh kosong.'
        elif not POLA_TELEPON.fullmatch(nilai):
            self.galat['telepon'] = 'Nomor telepon harus diawali 62 dan berisi 10–15 angka.'
        self.nilai['telepon'] = nilai

    def periksa(self):
        self._email()
        self._password()
        self._nama()
        self._alamat()
        self._telepon()
        # Password tidak pernah dikembalikan sebagai data isian.
        return self.nilai, self.galat
