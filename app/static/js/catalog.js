'use strict';

/* Katalog frontend demo: pencarian, filter, sorting, dan pagination berbagi satu hasil. */
class FilterKatalog {
    constructor() {
        this.pencarian = document.getElementById('catalogSearch');
        this.kategori = document.getElementById('catalogCategory');
        this.era = document.getElementById('catalogEra');
        this.kondisi = document.getElementById('catalogCondition');
        this.urutan = document.getElementById('catalogSort');
        this.grid = document.getElementById('catalogGrid');
        this.jumlah = document.getElementById('productCount');
        this.kosong = document.getElementById('catalogEmpty');
        this.pagination = document.getElementById('catalogPagination');
        this.perHalaman = 8;
        this.halamanAktif = 1;
    }

    normalisasi(teks) {
        return String(teks || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    }

    cocok(kartu) {
        const kataKunci = this.normalisasi(this.pencarian?.value || '');
        const kata = kataKunci.split(/\s+/).filter(Boolean);
        const teksProduk = this.normalisasi(kartu.dataset.search || kartu.dataset.name || '');
        const kategori = this.kategori?.value || '';
        const era = this.era?.value || '';
        const kondisi = this.kondisi?.value || '';
        return kata.every(item => teksProduk.includes(item))
            && (!kategori || kartu.dataset.category === kategori)
            && (!era || this.normalisasi(kartu.dataset.era).replace(/[–—]/g, '-') === this.normalisasi(era).replace(/[–—]/g, '-'))
            && (!kondisi || kartu.dataset.condition === kondisi);
    }

    urutkan(kartu) {
        const mode = this.urutan?.value || 'popular';
        return [...kartu].sort((a, b) => {
            if (mode === 'price-low') return Number(a.dataset.price) - Number(b.dataset.price);
            if (mode === 'price-high') return Number(b.dataset.price) - Number(a.dataset.price);
            if (mode === 'newest') return Number(b.dataset.id) - Number(a.dataset.id);
            return Number(b.dataset.rating) - Number(a.dataset.rating);
        });
    }

    renderPagination(total) {
        if (!this.pagination) return;
        const jumlahHalaman = Math.ceil(total / this.perHalaman);
        this.pagination.replaceChildren();
        this.pagination.hidden = jumlahHalaman <= 1;
        if (jumlahHalaman <= 1) return;

        const buatTombol = (label, halaman, opsi = {}) => {
            const tombol = document.createElement('button');
            tombol.type = 'button';
            tombol.textContent = label;
            tombol.className = 'pagination-button';
            if (halaman === this.halamanAktif) tombol.classList.add('active');
            if (opsi.disabled) tombol.disabled = true;
            if (opsi.label) tombol.setAttribute('aria-label', opsi.label);
            if (halaman === this.halamanAktif) tombol.setAttribute('aria-current', 'page');
            tombol.addEventListener('click', () => {
                this.halamanAktif = halaman;
                this.tampilkanHalaman();
                this.grid?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
            return tombol;
        };
        this.pagination.append(buatTombol('←', Math.max(1, this.halamanAktif - 1), { disabled: this.halamanAktif === 1, label: 'Halaman sebelumnya' }));
        for (let halaman = 1; halaman <= jumlahHalaman; halaman += 1) {
            this.pagination.append(buatTombol(String(halaman), halaman, { label: `Halaman ${halaman}` }));
        }
        this.pagination.append(buatTombol('→', Math.min(jumlahHalaman, this.halamanAktif + 1), { disabled: this.halamanAktif === jumlahHalaman, label: 'Halaman berikutnya' }));
    }

    tampilkanHalaman() {
        const kartu = [...(this.grid?.querySelectorAll('[data-product]') || [])];
        const cocok = kartu.filter(item => this.cocok(item));
        const terurut = this.urutkan(cocok);
        const jumlahHalaman = Math.max(1, Math.ceil(terurut.length / this.perHalaman));
        this.halamanAktif = Math.min(this.halamanAktif, jumlahHalaman);
        const awal = (this.halamanAktif - 1) * this.perHalaman;
        const terlihat = new Set(terurut.slice(awal, awal + this.perHalaman));

        // Urutan DOM diselaraskan dengan sorting, sedangkan pagination hanya menyembunyikan item di luar halaman.
        terurut.forEach(item => this.grid.appendChild(item));
        kartu.forEach(item => { item.hidden = !terlihat.has(item); });
        if (this.jumlah) this.jumlah.textContent = String(terurut.length);
        if (this.kosong) this.kosong.style.display = terurut.length ? 'none' : 'block';
        this.renderPagination(terurut.length);
    }

    terapkan(resetHalaman = true) {
        if (resetHalaman) this.halamanAktif = 1;
        this.tampilkanHalaman();
    }

    pasang() {
        [this.pencarian, this.kategori, this.era, this.kondisi].forEach(elemen => {
            elemen?.addEventListener(elemen === this.pencarian ? 'input' : 'change', () => this.terapkan(true));
        });
        this.urutan?.addEventListener('change', () => this.terapkan(true));
        this.terapkan(true);
    }
}

window.FilterKatalog = FilterKatalog;
