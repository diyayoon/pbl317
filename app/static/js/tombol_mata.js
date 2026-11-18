'use strict';

class TombolMata {
    constructor(tombol) {
        this.tombol = tombol;
        this.kolom = document.getElementById(tombol.getAttribute('aria-controls'));
    }

    aturVisibilitas(terlihat) {
        this.kolom.type = terlihat ? 'text' : 'password';
        this.tombol.setAttribute('aria-pressed', String(terlihat));

        const label = terlihat ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi';
        this.tombol.setAttribute('aria-label', label);
        this.tombol.setAttribute('title', label);
    }

    pasang() {
        if (!this.kolom) return;

        this.aturVisibilitas(false);
        this.tombol.addEventListener('click', () => {
            this.aturVisibilitas(this.kolom.type === 'password');
        });
        this.kolom.form?.addEventListener('submit', () => this.aturVisibilitas(false));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.password-toggle').forEach((tombol) => {
        new TombolMata(tombol).pasang();
    });
});
