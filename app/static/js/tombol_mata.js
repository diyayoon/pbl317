'use strict';

/* ======================================================================
   FILE   : tombol_mata.js
   ISI    : Tombol mata "tahan untuk melihat" pada kolom kata sandi.
            Dipakai halaman login. Perilakunya sama dengan halaman daftar
            (validasi_register.js), jadi file ini TIDAK dimuat di halaman daftar.
   ==================================================================== */

/* ===== KONSTANTA ===== */
const TEKS_TOMBOL_MATA_LOGIN = {
    id: 'Tahan untuk melihat kata sandi',
    en: 'Hold to show password',
};

/* ===== KELAS TOMBOL MATA ===== */
class TombolMata {
    constructor(tombol) {
        this.tombol = tombol;
        this.kolom = document.getElementById(tombol.getAttribute('aria-controls'));
    }

    /* ===== FUNGSI: BAHASA AKTIF ('id' ATAU 'en') ===== */
    bahasa() {
        const lang = document.documentElement.lang;
        if (lang === 'en' || lang === 'id') return lang;
        return localStorage.getItem('albis_antique_bahasa') === 'en' ? 'en' : 'id';
    }

    /* ===== FUNGSI: LABEL (aria-label + tooltip) SESUAI BAHASA ===== */
    perbaruiLabel() {
        const teks = TEKS_TOMBOL_MATA_LOGIN[this.bahasa()];
        this.tombol.setAttribute('aria-label', teks);
        this.tombol.setAttribute('title', teks);
    }

    /* ===== FUNGSI: MEMASANG PERISTIWA TAHAN / LEPAS ===== */
    pasang() {
        if (!this.kolom) return;

        const tampilkan = () => {
            this.kolom.type = 'text';
            this.tombol.setAttribute('aria-pressed', 'true');
        };
        const sembunyikan = () => {
            this.kolom.type = 'password';
            this.tombol.setAttribute('aria-pressed', 'false');
        };

        /* mouse / sentuh / pena */
        this.tombol.addEventListener('mousedown', (peristiwa) => peristiwa.preventDefault()); /* fokus tetap di kolom */
        this.tombol.addEventListener('pointerdown', tampilkan);
        this.tombol.addEventListener('pointerup', sembunyikan);
        this.tombol.addEventListener('pointerleave', sembunyikan);
        this.tombol.addEventListener('pointercancel', sembunyikan);
        this.tombol.addEventListener('contextmenu', (peristiwa) => peristiwa.preventDefault()); /* tahan lama di HP */

        /* keyboard: tahan Spasi atau Enter */
        this.tombol.addEventListener('keydown', (peristiwa) => {
            if (peristiwa.key === ' ' || peristiwa.key === 'Enter') {
                peristiwa.preventDefault();
                tampilkan();
            }
        });
        this.tombol.addEventListener('keyup', sembunyikan);

        /* pindah fokus / kirim form: kata sandi selalu kembali tersembunyi */
        this.tombol.addEventListener('blur', sembunyikan);
        this.kolom.form?.addEventListener('submit', sembunyikan);

        this.perbaruiLabel();
    }
}

/* ===== INISIALISASI ===== */
document.addEventListener('DOMContentLoaded', () => {
    const daftar = [...document.querySelectorAll('.password-toggle')].map((tombol) => new TombolMata(tombol));
    daftar.forEach((tombolMata) => tombolMata.pasang());

    /* ganti bahasa -> label ikut berganti */
    new MutationObserver(() => daftar.forEach((tombolMata) => tombolMata.perbaruiLabel())).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['lang'],
    });
});
