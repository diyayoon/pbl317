'use strict';

/* ===== KELAS EFEK KETIK ===== */
/* Mengetik teks elemen huruf demi huruf. Teks asli tetap ada (transparan) supaya
   tinggi layout tidak loncat dan screen reader tetap membaca kalimat utuh. */
class EfekKetik {
    constructor(elemen, { kecepatan = 42, jedaAwal = 400, saatSelesai = null } = {}) {
        this.elemen = elemen;
        this.kecepatan = kecepatan;
        this.jedaAwal = jedaAwal;
        this.saatSelesai = saatSelesai;
        this.timer = null;
        this.timerKursor = null;
        this.isi = null;
        this.kurangGerak = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    /* ===== FUNGSI: MENGAMBIL TEKS PENUH ELEMEN ===== */
    ambilTeks() {
        const hantu = this.elemen.querySelector('.ketik-hantu');
        return (hantu ? hantu.textContent : this.elemen.textContent).trim();
    }

    /* ===== FUNGSI: MENYUSUN LAPISAN TEKS HANTU + TEKS KETIK + KURSOR ===== */
    susun(teks) {
        const hantu = document.createElement('span');
        hantu.className = 'ketik-hantu';
        hantu.textContent = teks;

        const lapisan = document.createElement('span');
        lapisan.className = 'ketik-lapisan';
        lapisan.setAttribute('aria-hidden', 'true');

        this.isi = document.createElement('span');
        const kursor = document.createElement('span');
        kursor.className = 'ketik-kursor';

        lapisan.append(this.isi, kursor);
        this.elemen.classList.remove('ketik-selesai', 'ketik-kursor-hilang');
        this.elemen.classList.add('ketik-aktif');
        this.elemen.replaceChildren(hantu, lapisan);
    }

    /* ===== FUNGSI: MEMULAI ANIMASI KETIK ===== */
    mulai() {
        if (!this.elemen) return;
        this.hentikan();
        const teks = this.ambilTeks();
        if (!teks) return;

        if (this.kurangGerak) {
            this.selesaikan(false);
            return;
        }

        const huruf = Array.from(teks);
        this.susun(teks);

        let indeks = 0;
        const langkah = () => {
            if (indeks >= huruf.length) {
                this.selesaikan(true);
                return;
            }
            const karakter = huruf[indeks];
            this.isi.textContent += karakter;
            indeks += 1;
            const acak = 0.65 + Math.random() * 0.7;
            const jedaTandaBaca = ',.;:'.includes(karakter) ? 220 : 0;
            this.timer = window.setTimeout(langkah, this.kecepatan * acak + jedaTandaBaca);
        };
        this.timer = window.setTimeout(langkah, this.jedaAwal);
    }

    /* ===== FUNGSI: MENGETIK ULANG (DIPANGGIL SETELAH GANTI BAHASA) ===== */
    ulangi() {
        this.mulai();
    }

    /* ===== FUNGSI: MENGHENTIKAN TIMER ===== */
    hentikan() {
        window.clearTimeout(this.timer);
        window.clearTimeout(this.timerKursor);
    }

    /* ===== FUNGSI: MENANDAI SELESAI, MENYEMBUNYIKAN KURSOR SETELAH JEDA ===== */
    selesaikan(animasi) {
        this.elemen.classList.add('ketik-selesai');
        if (animasi) {
            this.timerKursor = window.setTimeout(
                () => this.elemen.classList.add('ketik-kursor-hilang'),
                2800,
            );
        }
        if (typeof this.saatSelesai === 'function') this.saatSelesai();
    }
}

/* ===== KELAS EFEK MUNCUL SAAT SCROLL ===== */
/* Elemen [data-muncul] naik pelan saat masuk layar. [data-muncul="berurutan"]
   membuat anak-anaknya muncul satu per satu. Tanpa JS / reduced motion: semua tampil biasa. */
class EfekMuncul {
    constructor(pemilih = '[data-muncul]') {
        this.pemilih = pemilih;
    }

    /* ===== FUNGSI: MEMASANG PENGAMAT SCROLL ===== */
    pasang() {
        const daftar = document.querySelectorAll(this.pemilih);
        const kurangGerak = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (!daftar.length || kurangGerak || !('IntersectionObserver' in window)) return;

        document.documentElement.classList.add('js-efek');
        daftar.forEach((elemen) => {
            if (elemen.dataset.muncul === 'berurutan') {
                [...elemen.children].forEach((anak, urutan) =>
                    anak.style.setProperty('--urutan', urutan),
                );
            }
        });

        const pengamat = new IntersectionObserver(
            (entri) => {
                entri.forEach((item) => {
                    if (!item.isIntersecting) return;
                    item.target.classList.add('terlihat');
                    pengamat.unobserve(item.target);
                });
            },
            { threshold: 0.12, rootMargin: '0px 0px -6% 0px' },
        );

        daftar.forEach((elemen) => pengamat.observe(elemen));
    }
}

window.EfekKetik = EfekKetik;
window.EfekMuncul = EfekMuncul;
