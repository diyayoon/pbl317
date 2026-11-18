'use strict';

/* ===== KAMUS PESAN VALIDASI ===== */
const PESAN_REGISTER = {
        email_wajib: 'Email tidak boleh kosong.',
        email_format: 'Format email tidak valid.',
        password_wajib: 'Kata sandi tidak boleh kosong.',
        password_pendek: 'Kata sandi minimal 16 karakter.',
        password_panjang: 'Kata sandi maksimal 128 karakter.',
        konfirmasi_wajib: 'Konfirmasi kata sandi wajib diisi.',
        konfirmasi_tidak_cocok: 'Konfirmasi kata sandi tidak cocok.',
        nama_wajib: 'Nama lengkap tidak boleh kosong.',
        nama_pendek: 'Nama lengkap minimal 3 karakter.',
        nama_format: 'Nama hanya boleh berisi huruf, spasi, titik, apostrof, dan tanda hubung.',
        alamat_wajib: 'Alamat tidak boleh kosong.',
        alamat_pendek: 'Alamat terlalu singkat; tuliskan minimal 10 karakter.',
        alamat_panjang: 'Alamat maksimal 255 karakter.',
        telepon_wajib: 'Nomor telepon tidak boleh kosong.',
        telepon_format: 'Nomor telepon harus diawali 62 dan berisi 10–15 angka.',
};

const MINIMAL_PASSWORD = 16;


/* ===== KELAS VALIDASI FORM REGISTER ===== */
/* Validasi di browser hanya untuk kenyamanan pengguna.
   Validasi yang sebenarnya tetap dilakukan server (app/utils/validasi.py). */
class ValidasiRegister {
    constructor(form) {
        this.form = form;
        this.sudahDisentuh = new Set();

        /* peta: id elemen -> { fungsi aturan, id elemen pesan error } */
        this.aturan = {
            email: { cek: () => this.cekEmail(), error: 'emailError' },
            password: { cek: () => this.cekPassword(), error: 'passwordError' },
            konfirmasiPassword: { cek: () => this.cekKonfirmasiPassword(), error: 'konfirmasiPasswordError' },
            nama: { cek: () => this.cekNama(), error: 'namaError' },
        };

        this.kolom = {};
        Object.keys(this.aturan).forEach((id) => {
            this.kolom[id] = document.getElementById(id);
        });
    }

    pesan(kode) {
        return PESAN_REGISTER[kode] || kode;
    }

    /* ===== ATURAN: EMAIL ===== */
    cekEmail() {
        const nilai = this.kolom.email.value.trim();
        if (!nilai) return 'email_wajib';
        if (nilai.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(nilai)) return 'email_format';
        return null;
    }

    /* ===== ATURAN: PASSWORD (hanya panjang: tanpa paksaan huruf besar / simbol) ===== */
    cekPassword() {
        const nilai = this.kolom.password.value;
        if (nilai.trim() === '') return 'password_wajib';
        if (nilai.length < MINIMAL_PASSWORD) return 'password_pendek';
        if (nilai.length > 128) return 'password_panjang';
        return null;
    }

    /* ===== ATURAN: KONFIRMASI PASSWORD ===== */
    cekKonfirmasiPassword() {
        const nilai = this.kolom.konfirmasiPassword.value;
        if (!nilai) return 'konfirmasi_wajib';
        if (nilai !== this.kolom.password.value) return 'konfirmasi_tidak_cocok';
        return null;
    }

    /* ===== ATURAN: NAMA ===== */
    cekNama() {
        const nilai = this.kolom.nama.value.trim().replace(/\s+/g, ' ');
        if (nilai === '') return 'nama_wajib';
        if (nilai.length < 3) return 'nama_pendek';
        if (nilai.length > 100 || !/^\p{L}[\p{L}\s.'-]*$/u.test(nilai)) return 'nama_format';
        return null;
    }

    /* ===== FUNGSI: MERAPIKAN NOMOR TELEPON (08xx / +62xx -> 62xx, hanya angka) ===== */
    normalisasiTelepon(teks) {
        let angka = teks.replace(/[^\d+]/g, '').replace(/^\+/, '').replace(/\+/g, '');
        if (angka.startsWith('0')) angka = `62${angka.slice(1)}`;
        return angka;
    }

    /* ===== FUNGSI: MENAMPILKAN / MENYEMBUNYIKAN ERROR PADA SATU KOLOM ===== */
    tampilkanHasil(id, kodeError) {
        const kolom = this.kolom[id];
        const pesanError = document.getElementById(this.aturan[id].error);
        if (!kolom || !pesanError) return;

        if (kodeError) {
            pesanError.textContent = this.pesan(kodeError);
            pesanError.dataset.kode = kodeError;
            pesanError.hidden = false;
            kolom.classList.add('is-invalid');
            kolom.classList.remove('is-valid');
            kolom.setAttribute('aria-invalid', 'true');
        } else {
            pesanError.textContent = '';
            delete pesanError.dataset.kode;
            pesanError.hidden = true;
            kolom.classList.remove('is-invalid');
            kolom.classList.add('is-valid');
            kolom.removeAttribute('aria-invalid');
        }
    }

    /* ===== FUNGSI: MEMVALIDASI SATU KOLOM ===== */
    validasiKolom(id) {
        const kodeError = this.aturan[id].cek();
        this.tampilkanHasil(id, kodeError);
        return kodeError === null;
    }

    /* ===== FUNGSI: MEMVALIDASI SEMUA KOLOM, MENGEMBALIKAN ID PERTAMA YANG SALAH ===== */
    validasiSemua() {
        let pertamaSalah = null;
        Object.keys(this.aturan).forEach((id) => {
            this.sudahDisentuh.add(id);
            const benar = this.validasiKolom(id);
            if (!benar && pertamaSalah === null) pertamaSalah = id;
        });
        return pertamaSalah;
    }

    /* ===== FUNGSI: LEVEL KEMAJUAN PANJANG PASSWORD (0-4; 4 = sudah 16 karakter) ===== */
    levelPanjang(jumlah) {
        if (jumlah === 0) return 0;
        if (jumlah >= MINIMAL_PASSWORD) return 4;
        if (jumlah >= 11) return 3;
        if (jumlah >= 6) return 2;
        return 1;
    }

    /* ===== FUNGSI: MEMPERBARUI GARIS KEMAJUAN + HITUNGAN "n / 16" ===== */
    perbaruiKekuatan() {
        const meter = document.getElementById('strengthMeter');
        const hitung = document.getElementById('passwordCount');
        const jumlah = this.kolom.password.value.length;
        if (meter) meter.dataset.level = String(this.levelPanjang(jumlah));
        if (hitung) {
            hitung.textContent = `${jumlah} / ${MINIMAL_PASSWORD}`;
            hitung.classList.toggle('tercapai', jumlah >= MINIMAL_PASSWORD);
        }
    }

    /* ===== FUNGSI: MEMASANG SEMUA EVENT FORM ===== */
    pasang() {
        /* pengaman: jangan pasang event dua kali jika init terpanggil ganda */
        if (this.form.dataset.validasiAktif === '1') return;
        this.form.dataset.validasiAktif = '1';

        Object.keys(this.aturan).forEach((id) => {
            const kolom = this.kolom[id];
            if (!kolom) return;

            /* kolom yang sudah membawa error dari server langsung dianggap disentuh */
            if (kolom.classList.contains('is-invalid')) this.sudahDisentuh.add(id);

            kolom.addEventListener('blur', () => {
                if (!['password', 'konfirmasiPassword'].includes(id) && kolom.value !== kolom.value.trim()) {
                    kolom.value = kolom.value.trim();
                }
                this.sudahDisentuh.add(id);
                this.validasiKolom(id);
            });

            kolom.addEventListener('input', () => {
                if (id === 'password') {
                    this.perbaruiKekuatan();
                    if (this.sudahDisentuh.has('konfirmasiPassword')) this.validasiKolom('konfirmasiPassword');
                }
                if (id === 'konfirmasiPassword' && this.sudahDisentuh.has('konfirmasiPassword')) this.validasiKolom('konfirmasiPassword');
                if (this.sudahDisentuh.has(id)) this.validasiKolom(id);
            });
        });

        this.form.addEventListener('submit', (event) => {
            const pertamaSalah = this.validasiSemua();
            if (pertamaSalah !== null) {
                event.preventDefault();
                this.kolom[pertamaSalah].focus();
                return;
            }
            const tombolKirim = this.form.querySelector('button[type="submit"]');
            if (tombolKirim) tombolKirim.disabled = true; /* cegah kirim ganda */
        });

        this.perbaruiKekuatan();

    }
}

/* ===== INISIALISASI ===== */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('formRegister');
    if (form) new ValidasiRegister(form).pasang();
});
