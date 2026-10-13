'use strict';

/* ===== KAMUS PESAN ERROR (ID / EN) ===== */
const PESAN_REGISTER = {
    id: {
        username_wajib: 'Username tidak boleh kosong.',
        username_pendek: 'Username minimal 3 karakter.',
        username_format: 'Username hanya boleh huruf, angka, titik, dan garis bawah (maksimal 30 karakter).',
        password_wajib: 'Password tidak boleh kosong.',
        password_pendek: 'Password minimal 16 karakter.',
        password_panjang: 'Password maksimal 128 karakter.',
        nama_wajib: 'Nama tidak boleh kosong.',
        nama_pendek: 'Nama minimal 2 karakter.',
        nama_format: 'Nama hanya boleh berisi huruf, spasi, titik, apostrof, dan tanda hubung.',
        lahir_wajib: 'Tanggal lahir tidak boleh kosong.',
        lahir_masa_depan: 'Tanggal lahir tidak boleh di masa depan.',
        lahir_terlalu_tua: 'Tanggal lahir tidak valid (lebih dari 120 tahun lalu).',
        alamat_wajib: 'Alamat tidak boleh kosong.',
        alamat_pendek: 'Alamat terlalu singkat, tuliskan minimal 10 karakter.',
        alamat_panjang: 'Alamat maksimal 255 karakter.',
        telepon_wajib: 'Nomor telepon tidak boleh kosong.',
        telepon_format: 'Nomor telepon harus diawali 62 dan berisi 10-15 angka.',
    },
    en: {
        username_wajib: 'Username is required.',
        username_pendek: 'Username must be at least 3 characters.',
        username_format: 'Username may only contain letters, numbers, dots, and underscores (max 30 characters).',
        password_wajib: 'Password is required.',
        password_pendek: 'Password must be at least 16 characters.',
        password_panjang: 'Password must be at most 128 characters.',
        nama_wajib: 'Name is required.',
        nama_pendek: 'Name must be at least 2 characters.',
        nama_format: 'Name may only contain letters, spaces, dots, apostrophes, and hyphens.',
        lahir_wajib: 'Date of birth is required.',
        lahir_masa_depan: 'Date of birth cannot be in the future.',
        lahir_terlalu_tua: 'Date of birth is not valid (more than 120 years ago).',
        alamat_wajib: 'Address is required.',
        alamat_pendek: 'Address is too short, please enter at least 10 characters.',
        alamat_panjang: 'Address must be at most 255 characters.',
        telepon_wajib: 'Phone number is required.',
        telepon_format: 'Phone number must start with 62 and contain 10-15 digits.',
    },
};

const MINIMAL_PASSWORD = 16;

const TEKS_TOMBOL_MATA = {
    id: 'Tahan untuk melihat kata sandi',
    en: 'Hold to show password',
};

/* ===== KELAS VALIDASI FORM REGISTER ===== */
/* Validasi di browser hanya untuk kenyamanan pengguna.
   Validasi yang sebenarnya tetap dilakukan server (app/utils/validasi.py). */
class ValidasiRegister {
    constructor(form) {
        this.form = form;
        this.sudahDisentuh = new Set();

        /* peta: id elemen -> { fungsi aturan, id elemen pesan error } */
        this.aturan = {
            username: { cek: () => this.cekUsername(), error: 'usernameError' },
            password: { cek: () => this.cekPassword(), error: 'passwordError' },
            nama: { cek: () => this.cekNama(), error: 'namaError' },
            tanggalLahir: { cek: () => this.cekTanggalLahir(), error: 'tanggalLahirError' },
            alamat: { cek: () => this.cekAlamat(), error: 'alamatError' },
            telepon: { cek: () => this.cekTelepon(), error: 'teleponError' },
        };

        this.kolom = {};
        Object.keys(this.aturan).forEach((id) => {
            this.kolom[id] = document.getElementById(id);
        });
    }

    /* ===== FUNGSI: BAHASA AKTIF ('id' ATAU 'en') ===== */
    bahasa() {
        const lang = document.documentElement.lang;
        if (lang === 'en' || lang === 'id') return lang;
        return localStorage.getItem('albis_antique_bahasa') === 'en' ? 'en' : 'id';
    }

    /* ===== FUNGSI: MENGAMBIL TEKS PESAN DARI KODE ===== */
    pesan(kode) {
        return PESAN_REGISTER[this.bahasa()][kode] || kode;
    }

    /* ===== ATURAN: USERNAME ===== */
    cekUsername() {
        const nilai = this.kolom.username.value.trim();
        if (nilai === '') return 'username_wajib';
        if (nilai.length < 3) return 'username_pendek';
        if (nilai.length > 30 || !/^[A-Za-z0-9_.]+$/.test(nilai)) return 'username_format';
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

    /* ===== ATURAN: NAMA ===== */
    cekNama() {
        const nilai = this.kolom.nama.value.trim().replace(/\s+/g, ' ');
        if (nilai === '') return 'nama_wajib';
        if (nilai.length < 2) return 'nama_pendek';
        if (!/^\p{L}[\p{L}\s.'-]*$/u.test(nilai)) return 'nama_format';
        return null;
    }

    /* ===== ATURAN: TANGGAL LAHIR ===== */
    cekTanggalLahir() {
        const nilai = this.kolom.tanggalLahir.value;
        if (nilai === '') return 'lahir_wajib';
        if (nilai > this.tanggalHariIni()) return 'lahir_masa_depan';
        if (nilai < this.tanggalBatasBawah()) return 'lahir_terlalu_tua';
        return null;
    }

    /* ===== ATURAN: ALAMAT ===== */
    cekAlamat() {
        const nilai = this.kolom.alamat.value.trim();
        if (nilai === '') return 'alamat_wajib';
        if (nilai.length < 10) return 'alamat_pendek';
        if (nilai.length > 255) return 'alamat_panjang';
        return null;
    }

    /* ===== ATURAN: NOMOR TELEPON ===== */
    cekTelepon() {
        const nilai = this.normalisasiTelepon(this.kolom.telepon.value);
        if (nilai === '') return 'telepon_wajib';
        if (!/^62\d{8,13}$/.test(nilai)) return 'telepon_format';
        return null;
    }

    /* ===== FUNGSI: MERAPIKAN NOMOR TELEPON (08xx / +62xx -> 62xx, hanya angka) ===== */
    normalisasiTelepon(teks) {
        let angka = teks.replace(/[^\d+]/g, '').replace(/^\+/, '').replace(/\+/g, '');
        if (angka.startsWith('0')) angka = `62${angka.slice(1)}`;
        return angka;
    }

    /* ===== FUNGSI: TANGGAL HARI INI FORMAT YYYY-MM-DD (WAKTU LOKAL, BUKAN UTC) ===== */
    tanggalHariIni() {
        return this.formatTanggal(new Date());
    }

    /* ===== FUNGSI: BATAS TANGGAL LAHIR PALING LAMA (120 TAHUN LALU) ===== */
    tanggalBatasBawah() {
        const batas = new Date();
        batas.setFullYear(batas.getFullYear() - 120);
        return this.formatTanggal(batas);
    }

    /* ===== FUNGSI: FORMAT DATE -> YYYY-MM-DD ===== */
    formatTanggal(tanggal) {
        const bulan = String(tanggal.getMonth() + 1).padStart(2, '0');
        const hari = String(tanggal.getDate()).padStart(2, '0');
        return `${tanggal.getFullYear()}-${bulan}-${hari}`;
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

    /* ===== FUNGSI: MEMPERBARUI PENGHITUNG KARAKTER ALAMAT ===== */
    perbaruiHitungAlamat() {
        const penghitung = document.getElementById('alamatCount');
        if (penghitung) penghitung.textContent = `${this.kolom.alamat.value.length} / 255`;
    }

    /* ===== FUNGSI: MENAMPILKAN ULANG PESAN ERROR SETELAH GANTI BAHASA ===== */
    perbaruiBahasa() {
        Object.keys(this.aturan).forEach((id) => {
            const pesanError = document.getElementById(this.aturan[id].error);
            if (pesanError && pesanError.dataset.kode) {
                pesanError.textContent = this.pesan(pesanError.dataset.kode);
            }
        });
        this.perbaruiLabelTombolMata();
    }

    /* ===== FUNGSI: LABEL (aria-label + tooltip) TOMBOL MATA SESUAI BAHASA ===== */
    perbaruiLabelTombolMata() {
        const tombol = document.getElementById('togglePassword');
        if (!tombol) return;
        const teks = TEKS_TOMBOL_MATA[this.bahasa()];
        tombol.setAttribute('aria-label', teks);
        tombol.setAttribute('title', teks);
    }

    /* ===== FUNGSI: TOMBOL MATA, TAHAN UNTUK MELIHAT, LEPAS UNTUK MENYEMBUNYIKAN ===== */
    pasangTombolPassword() {
        const tombol = document.getElementById('togglePassword');
        if (!tombol) return;

        const tampilkan = () => {
            this.kolom.password.type = 'text';
            tombol.setAttribute('aria-pressed', 'true');
        };
        const sembunyikan = () => {
            this.kolom.password.type = 'password';
            tombol.setAttribute('aria-pressed', 'false');
        };

        /* mouse / sentuh / pena */
        tombol.addEventListener('mousedown', (event) => event.preventDefault()); /* fokus tetap di kolom */
        tombol.addEventListener('pointerdown', tampilkan);
        tombol.addEventListener('pointerup', sembunyikan);
        tombol.addEventListener('pointerleave', sembunyikan);
        tombol.addEventListener('pointercancel', sembunyikan);
        tombol.addEventListener('contextmenu', (event) => event.preventDefault()); /* tahan lama di HP */

        /* keyboard: tahan Spasi atau Enter */
        tombol.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                tampilkan();
            }
        });
        tombol.addEventListener('keyup', sembunyikan);

        /* pengaman: pindah fokus / ganti tab / kirim form -> selalu tersembunyi lagi */
        tombol.addEventListener('blur', sembunyikan);
        window.addEventListener('blur', sembunyikan);
        this.form.addEventListener('submit', sembunyikan);
    }

    /* ===== FUNGSI: MEMASANG SEMUA EVENT FORM ===== */
    pasang() {
        /* pengaman: jangan pasang event dua kali jika init terpanggil ganda */
        if (this.form.dataset.validasiAktif === '1') return;
        this.form.dataset.validasiAktif = '1';

        /* batas tanggal pada kalender */
        if (this.kolom.tanggalLahir) {
            this.kolom.tanggalLahir.max = this.tanggalHariIni();
            this.kolom.tanggalLahir.min = this.tanggalBatasBawah();
        }

        Object.keys(this.aturan).forEach((id) => {
            const kolom = this.kolom[id];
            if (!kolom) return;

            /* kolom yang sudah membawa error dari server langsung dianggap disentuh */
            if (kolom.classList.contains('is-invalid')) this.sudahDisentuh.add(id);

            kolom.addEventListener('blur', () => {
                if (id === 'telepon' && kolom.value.trim() !== '') {
                    kolom.value = this.normalisasiTelepon(kolom.value);
                }
                if (id !== 'password' && kolom.value !== kolom.value.trim()) {
                    kolom.value = kolom.value.trim();
                }
                this.sudahDisentuh.add(id);
                this.validasiKolom(id);
            });

            kolom.addEventListener('input', () => {
                if (id === 'password') this.perbaruiKekuatan();
                if (id === 'alamat') this.perbaruiHitungAlamat();
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

        this.pasangTombolPassword();
        this.perbaruiLabelTombolMata();
        this.perbaruiKekuatan();
        this.perbaruiHitungAlamat();

        /* ganti bahasa -> pesan error ikut berganti */
        new MutationObserver(() => this.perbaruiBahasa()).observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['lang'],
        });
    }
}

/* ===== INISIALISASI ===== */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('formRegister');
    if (form) new ValidasiRegister(form).pasang();
});
