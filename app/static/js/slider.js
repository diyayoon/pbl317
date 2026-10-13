'use strict';

/* ======================================================================
   FILE   : slider.js
   ISI    : Slider produk unggulan di hero beranda
   FITUR  : geser otomatis, seret (mouse) / usap (sentuh), panah, titik,
            tombol jeda, berhenti saat disorot atau tab tidak aktif,
            dan tidak jalan otomatis bila pengguna meminta gerak minimal.
   DAFTAR BAGIAN (cari dengan Ctrl+F: "=====" + nama):
      1. KONSTANTA
      2. KELAS SLIDER HERO
      3. INISIALISASI
   ==================================================================== */

/* ===== KONSTANTA ===== */
const JEDA_BAWAAN = 8500; /* ms antar slide */
const AMBANG_GESER = 0.18; /* geseran minimal (rasio lebar) agar pindah slide */
const AMBANG_KECEPATAN = 0.45; /* px per ms: sentakan cepat tetap memindahkan slide */

const TEKS_SLIDER = {
    id: {
        sebelumnya: 'Slide sebelumnya',
        berikutnya: 'Slide berikutnya',
        jeda: 'Jeda pergantian otomatis',
        putar: 'Putar pergantian otomatis',
        ke: (nomor) => `Ke slide ${nomor}`,
    },
    en: {
        sebelumnya: 'Previous slide',
        berikutnya: 'Next slide',
        jeda: 'Pause automatic rotation',
        putar: 'Start automatic rotation',
        ke: (nomor) => `Go to slide ${nomor}`,
    },
};

/* ===== KELAS SLIDER HERO ===== */
class SliderHero {
    constructor(akar) {
        this.akar = akar;
        this.viewport = akar.querySelector('.slider-viewport');
        this.slide = [...akar.querySelectorAll('.slider-slide')];
        this.jumlah = this.slide.length;
        this.wadahDot = akar.querySelector('.slider-dots');
        this.tombolJeda = akar.querySelector('.slider-jeda');
        this.jeda = Number(akar.dataset.jeda) || JEDA_BAWAAN;

        this.indeks = 0;
        this.pewaktu = null;
        this.dots = [];

        /* Penyebab slider berhenti sementara */
        this.jedaManual = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        this.tertahan = false; /* kursor di atas slider / fokus keyboard di dalamnya */
        this.tersembunyi = document.hidden; /* tab sedang tidak aktif */
        this.terlihat = true; /* slider ada di layar */
        this.sedangMenggeser = false;
        this.barusajaGeser = false;
    }

    /* ===== FUNGSI: BAHASA AKTIF ('id' ATAU 'en') ===== */
    bahasa() {
        const lang = document.documentElement.lang;
        if (lang === 'en' || lang === 'id') return lang;
        return localStorage.getItem('albis_antique_bahasa') === 'en' ? 'en' : 'id';
    }

    /* ===== FUNGSI: MENJALANKAN SLIDER ===== */
    mulai() {
        if (this.jumlah < 2) return; /* satu slide saja: tampilkan apa adanya */

        this.buatDot();
        this.pasangKontrol();
        this.pasangGeser();
        this.pasangPenahan();
        this.akar.classList.add('is-siap');
        this.perbaruiLabel();
        this.render();
        this.jadwalkan();

        /* ganti bahasa -> label tombol ikut berganti */
        new MutationObserver(() => this.perbaruiLabel()).observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['lang'],
        });
    }

    /* ===== FUNGSI: MEMBUAT TITIK NAVIGASI ===== */
    buatDot() {
        this.slide.forEach((_, nomor) => {
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'slider-dot';
            dot.addEventListener('click', () => this.pindahKe(nomor));
            this.wadahDot.append(dot);
            this.dots.push(dot);
        });
    }

    /* ===== FUNGSI: MEMPERBARUI LABEL ARIA TOMBOL SESUAI BAHASA ===== */
    perbaruiLabel() {
        const teks = TEKS_SLIDER[this.bahasa()];
        this.akar.querySelectorAll('[data-slider]').forEach((tombol) => {
            tombol.setAttribute('aria-label', teks[tombol.dataset.slider]);
        });
        this.dots.forEach((dot, nomor) => dot.setAttribute('aria-label', teks.ke(nomor + 1)));
        this.perbaruiTampilanJeda();
    }

    /* ===== FUNGSI: MENATA POSISI SETIAP SLIDE SECARA MELINGKAR ===== */
    render() {
        const separuh = this.jumlah / 2;
        this.slide.forEach((el, nomor) => {
            let selisih = (nomor - this.indeks + this.jumlah) % this.jumlah;
            if (selisih > separuh) selisih -= this.jumlah; /* slide terjauh dipindah ke sisi terdekat */
            const aktif = selisih === 0;
            el.style.setProperty('--posisi', String(selisih));
            el.classList.toggle('is-aktif', aktif);
            el.classList.toggle('is-jauh', Math.abs(selisih) > 1);
            el.setAttribute('aria-hidden', String(!aktif));
            el.inert = !aktif; /* tautan di slide tersembunyi tidak bisa difokus */
        });
        this.dots.forEach((dot, nomor) => {
            dot.setAttribute('aria-current', String(nomor === this.indeks));
        });
    }

    /* ===== FUNGSI: PINDAH KE SLIDE TERTENTU ===== */
    pindahKe(nomor) {
        this.indeks = ((nomor % this.jumlah) + this.jumlah) % this.jumlah;
        this.render();
        this.jadwalkan();
    }

    berikutnya() {
        this.pindahKe(this.indeks + 1);
    }

    sebelumnya() {
        this.pindahKe(this.indeks - 1);
    }

    /* ===== FUNGSI: BOLEHKAH SLIDER BERGERAK OTOMATIS SEKARANG ===== */
    bolehJalan() {
        return !this.jedaManual && !this.tertahan && !this.tersembunyi && this.terlihat && !this.sedangMenggeser;
    }

    /* ===== FUNGSI: MENJADWALKAN PERGANTIAN BERIKUTNYA (ATAU MENGHENTIKANNYA) ===== */
    jadwalkan() {
        window.clearTimeout(this.pewaktu);
        this.perbaruiTampilanJeda();
        if (!this.bolehJalan()) return;
        this.pewaktu = window.setTimeout(() => this.berikutnya(), this.jeda);
    }

    /* ===== FUNGSI: MENYESUAIKAN TOMBOL JEDA DAN PENGUMUMAN PEMBACA LAYAR ===== */
    perbaruiTampilanJeda() {
        const teks = TEKS_SLIDER[this.bahasa()];
        if (this.tombolJeda) {
            this.tombolJeda.dataset.berjalan = String(!this.jedaManual);
            this.tombolJeda.setAttribute('aria-label', this.jedaManual ? teks.putar : teks.jeda);
        }
        /* saat berputar sendiri jangan umumkan tiap slide; saat manual, umumkan */
        this.viewport.setAttribute('aria-live', this.jedaManual ? 'polite' : 'off');
    }

    /* ===== FUNGSI: PANAH, TOMBOL JEDA, DAN PANAH KEYBOARD ===== */
    pasangKontrol() {
        this.akar.querySelector('[data-slider="sebelumnya"]').addEventListener('click', () => this.sebelumnya());
        this.akar.querySelector('[data-slider="berikutnya"]').addEventListener('click', () => this.berikutnya());

        this.tombolJeda?.addEventListener('click', () => {
            this.jedaManual = !this.jedaManual;
            this.jadwalkan();
        });

        this.akar.addEventListener('keydown', (peristiwa) => {
            if (peristiwa.key === 'ArrowLeft') {
                peristiwa.preventDefault();
                this.sebelumnya();
            } else if (peristiwa.key === 'ArrowRight') {
                peristiwa.preventDefault();
                this.berikutnya();
            }
        });
    }

    /* ===== FUNGSI: BERHENTI SAAT DISOROT, DIFOKUS KEYBOARD, TAB TERSEMBUNYI, ATAU DI LUAR LAYAR ===== */
    pasangPenahan() {
        /* hanya mouse: pada layar sentuh "hover" menempel setelah ketukan */
        this.akar.addEventListener('pointerenter', (peristiwa) => {
            if (peristiwa.pointerType !== 'mouse') return;
            this.tertahan = true;
            this.jadwalkan();
        });
        this.akar.addEventListener('pointerleave', (peristiwa) => {
            if (peristiwa.pointerType !== 'mouse') return;
            this.tertahan = false;
            this.jadwalkan();
        });

        /* fokus keyboard menahan; klik mouse pada tombol tidak (agar tidak macet) */
        this.akar.addEventListener('focusin', (peristiwa) => {
            if (!peristiwa.target.matches(':focus-visible')) return;
            this.tertahan = true;
            this.jadwalkan();
        });
        this.akar.addEventListener('focusout', (peristiwa) => {
            if (this.akar.contains(peristiwa.relatedTarget)) return;
            this.tertahan = false;
            this.jadwalkan();
        });

        document.addEventListener('visibilitychange', () => {
            this.tersembunyi = document.hidden;
            this.jadwalkan();
        });

        if ('IntersectionObserver' in window) {
            new IntersectionObserver(
                ([entri]) => {
                    this.terlihat = entri.isIntersecting;
                    this.jadwalkan();
                },
                { threshold: 0.35 },
            ).observe(this.akar);
        }
    }

    /* ===== FUNGSI: GESER DENGAN MOUSE / JARI (POINTER EVENTS) ===== */
    pasangGeser() {
        const viewport = this.viewport;
        let idPointer = null;
        let mulaiX = 0;
        let mulaiY = 0;
        let mulaiWaktu = 0;
        let siap = false; /* tombol sudah ditekan */
        let menggeser = false; /* sudah melewati ambang gerak */
        let dx = 0;

        /* tautan / foto di dalam slide tidak boleh memulai "drag tautan" bawaan browser (itu membatalkan seretan slider) */
        viewport.addEventListener('dragstart', (peristiwa) => peristiwa.preventDefault());

        viewport.addEventListener('pointerdown', (peristiwa) => {
            if (peristiwa.pointerType === 'mouse' && peristiwa.button !== 0) return;
            idPointer = peristiwa.pointerId;
            mulaiX = peristiwa.clientX;
            mulaiY = peristiwa.clientY;
            mulaiWaktu = performance.now();
            siap = true;
            menggeser = false;
            dx = 0;
        });

        viewport.addEventListener('pointermove', (peristiwa) => {
            if (!siap || peristiwa.pointerId !== idPointer) return;
            dx = peristiwa.clientX - mulaiX;
            const dy = peristiwa.clientY - mulaiY;

            if (!menggeser) {
                /* abaikan gerak kecil dan gerak yang lebih condong vertikal (itu scroll halaman) */
                if (Math.abs(dx) < 6 || Math.abs(dx) < Math.abs(dy)) return;
                menggeser = true;
                this.sedangMenggeser = true;
                viewport.setPointerCapture(idPointer);
                viewport.classList.add('is-menggeser');
                this.jadwalkan();
            }
            viewport.style.setProperty('--geser', `${dx}px`);
        });

        const selesai = (peristiwa, dibatalkan) => {
            if (!siap || peristiwa.pointerId !== idPointer) return;
            siap = false;
            if (!menggeser) return;

            const lebar = viewport.clientWidth || 1;
            const kecepatan = Math.abs(dx) / Math.max(1, performance.now() - mulaiWaktu);
            const cukupJauh = Math.abs(dx) > lebar * AMBANG_GESER;
            const sentakan = kecepatan > AMBANG_KECEPATAN && Math.abs(dx) > 24;

            viewport.classList.remove('is-menggeser');
            viewport.style.setProperty('--geser', '0px');
            this.sedangMenggeser = false;

            /* cegah klik tautan yang ikut terpicu setelah menyeret */
            this.barusajaGeser = true;
            window.setTimeout(() => {
                this.barusajaGeser = false;
            }, 60);

            if (!dibatalkan && (cukupJauh || sentakan)) {
                if (dx < 0) this.berikutnya();
                else this.sebelumnya();
            } else {
                this.jadwalkan();
            }
        };

        viewport.addEventListener('pointerup', (peristiwa) => selesai(peristiwa, false));
        viewport.addEventListener('pointercancel', (peristiwa) => selesai(peristiwa, true));

        viewport.addEventListener(
            'click',
            (peristiwa) => {
                if (!this.barusajaGeser) return;
                peristiwa.preventDefault();
                peristiwa.stopPropagation();
            },
            true,
        );
    }
}

/* ===== INISIALISASI ===== */
document.addEventListener('DOMContentLoaded', () => {
    const akar = document.getElementById('heroSlider');
    if (akar) new SliderHero(akar).mulai();
});
