'use strict';

/* ===== KELAS EFEK SALJU ===== */
class EfekSalju {
    constructor(wadah) {
        this.wadah = wadah;
        this.intervalId = null;
        this.jeda = 520;
        this.maksimalButir = 100;
        this.sedangScroll = false;
        this.timerScroll = null;
    }

    /* ===== FUNGSI: MENAHAN SALJU BARU SAAT HALAMAN DI-SCROLL (MENCEGAH GLITCH RENDER) ===== */
    pantauScroll() {
        window.addEventListener(
            'scroll',
            () => {
                this.sedangScroll = true;
                window.clearTimeout(this.timerScroll);
                this.timerScroll = window.setTimeout(() => {
                    this.sedangScroll = false;
                }, 220);
            },
            { passive: true }
        );
    }

    /* ===== FUNGSI: MEMBUAT SATU BUTIR SALJU ===== */
    buatButirSalju() {
        if (!this.wadah || document.hidden || this.sedangScroll) return;
        if (this.wadah.childElementCount >= this.maksimalButir) return;

        const butir = document.createElement('span');
        const varian = Math.random();
        butir.className = `snowflake ${varian > 0.66 ? 'snowflake-deep' : varian > 0.33 ? 'snowflake-soft' : 'snowflake-white'}`;
        butir.textContent = Math.random() > 0.55 ? '❅' : '❄';
        butir.style.left = `${Math.random() * 100}%`;
        butir.style.fontSize = `${9 + Math.random() * 14}px`;
        butir.style.opacity = `${0.34 + Math.random() * 0.52}`;
        butir.style.setProperty('--drift', `${-75 + Math.random() * 150}px`);
        butir.style.animationDuration = `${7 + Math.random() * 8}s`;
        butir.style.animationDelay = `${Math.random() * -3}s`;
        this.wadah.appendChild(butir);
        butir.addEventListener('animationend', () => butir.remove(), { once: true });
    }

    /* ===== FUNGSI: MEMBUAT SALJU AWAL AGAR LANGSUNG TERLIHAT ===== */
    buatSaljuAwal(jumlah = 12) {
        for (let indeks = 0; indeks < jumlah; indeks += 1) {
            window.setTimeout(() => this.buatButirSalju(), indeks * 45);
        }
    }

    /* ===== FUNGSI: MEMULAI SNOWFALL ===== */
    mulai() {
        if (!this.wadah || this.intervalId) return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        this.pantauScroll();
        this.buatSaljuAwal();
        this.intervalId = window.setInterval(() => this.buatButirSalju(), this.jeda);
    }

    /* ===== FUNGSI: MENGHENTIKAN SNOWFALL ===== */
    berhenti() {
        if (!this.intervalId) return;
        window.clearInterval(this.intervalId);
        this.intervalId = null;
    }
}

window.EfekSalju = EfekSalju;
