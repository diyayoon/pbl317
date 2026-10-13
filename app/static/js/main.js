'use strict';


function tampilkanPromptLogin(jenisAksi = 'wishlist') {
    const sudahAda = document.querySelector('.albis-auth-prompt');
    if (sudahAda) return;

    const isWishlist = jenisAksi === 'wishlist';
    const overlay = document.createElement('div');
    overlay.className = 'albis-auth-prompt';
    overlay.setAttribute('role', 'presentation');
    overlay.innerHTML = `
        <section class="albis-auth-dialog" role="dialog" aria-modal="true"
                 aria-labelledby="albisAuthTitle" aria-describedby="albisAuthDescription">
            <button class="albis-auth-close" type="button" aria-label="Tutup dialog">×</button>
            <div class="albis-auth-crest" aria-hidden="true">♔</div>
            <h2 id="albisAuthTitle">Simpan koleksi favoritmu</h2>
            <p id="albisAuthDescription">${
                isWishlist
                    ? 'Masuk ke akun Albis Antique untuk menyimpan benda antik pilihanmu ke wishlist.'
                    : 'Masuk terlebih dahulu agar koleksi pilihanmu bisa disimpan di keranjang.'
            }</p>
            <div class="albis-auth-actions">
                <button class="albis-auth-later" type="button">Nanti saja</button>
                <a class="albis-auth-login" href="${document.body.dataset.loginUrl || '/login'}">Masuk</a>
            </div>
        </section>`;
    document.body.append(overlay);
    document.body.classList.add('lightbox-terbuka');

    const tutup = () => {
        overlay.remove();
        document.body.classList.remove('lightbox-terbuka');
        document.removeEventListener('keydown', tombolEscape);
    };
    const tombolEscape = (event) => {
        if (event.key === 'Escape') tutup();
    };
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay || event.target.closest('.albis-auth-close, .albis-auth-later')) tutup();
    });
    document.addEventListener('keydown', tombolEscape);
    overlay.querySelector('.albis-auth-later').focus();
}

function tampilkanToast(pesan) {
    let toast = document.getElementById('albisToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'albisToast';
        toast.className = 'albis-toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        document.body.append(toast);
    }
    toast.textContent = pesan;
    toast.classList.add('is-visible');
    window.clearTimeout(toast._timer);
    toast._timer = window.setTimeout(() => toast.classList.remove('is-visible'), 2200);
}


/* ===== PENYIMPAN KERANJANG PROTOTIPE FRONTEND =====
   Data disimpan di localStorage untuk demo; bukan pengganti penyimpanan database. */
class KeranjangPrototype {
    constructor() { this.kunci = 'albis_antique_cart_demo'; }
    ambilData() {
        try { return JSON.parse(localStorage.getItem(this.kunci)) || []; }
        catch { return []; }
    }
    simpan(data) {
        localStorage.setItem(this.kunci, JSON.stringify(data));
        this.perbaruiBadge();
    }
    tambahProduk(idProduk, detail = {}) {
        const data = this.ambilData();
        const produk = data.find(item => Number(item.id) === Number(idProduk));
        if (produk) {
            Object.assign(produk, detail);
            produk.jumlah = Number(produk.jumlah || 0) + 1;
        } else data.push({ ...detail, id: Number(idProduk), jumlah: 1 });
        this.simpan(data);
    }
    ubahJumlah(idProduk, delta) {
        const data = this.ambilData().map(item => Number(item.id) === Number(idProduk)
            ? { ...item, jumlah: Math.max(0, Number(item.jumlah || 1) + delta) } : item
        ).filter(item => item.jumlah > 0);
        this.simpan(data);
        renderKeranjang(data);
    }
    hapus(idProduk) {
        const data = this.ambilData().filter(item => Number(item.id) !== Number(idProduk));
        this.simpan(data);
        renderKeranjang(data);
    }
    perbaruiBadge() {
        const badge = document.getElementById('cartBadge');
        if (!badge) return;
        const total = this.ambilData().reduce((jumlah, item) => jumlah + Number(item.jumlah || 1), 0);
        badge.textContent = String(total);
        badge.hidden = total === 0;
    }
}

const KUNCI_WISHLIST = 'albis_antique_wishlist_demo';
function ambilWishlist() {
    try { return JSON.parse(localStorage.getItem(KUNCI_WISHLIST)) || []; }
    catch { return []; }
}
function simpanWishlist(data) {
    localStorage.setItem(KUNCI_WISHLIST, JSON.stringify(data));
    perbaruiWishlistBadge();
}
function perbaruiWishlistBadge() {
    // Wishlist diakses melalui dashboard akun, bukan ikon header.
    // Fungsi tetap tersedia agar pemanggilan setelah perubahan data aman.
}
function ambilDetailProduk(tombol) {
    const kartu = tombol.closest('[data-product]');
    if (!kartu) return {
        id: Number(tombol.dataset.productId || tombol.dataset.addCart),
        nama: tombol.dataset.productName || 'Produk Albis Antique',
        harga: Number(tombol.dataset.productPrice) || 0,
        gambar: tombol.dataset.productImage || '',
        kategori: tombol.dataset.productCategory || '',
        asal: tombol.dataset.productOrigin || '',
        url: tombol.dataset.productUrl || '',
    };
    const hargaTeks = kartu.querySelector('.price')?.textContent || '';
    const harga = Number(hargaTeks.replace(/[^0-9]/g, '')) || Number(kartu.dataset.price) || 0;
    return {
        id: Number(kartu.dataset.id),
        nama: kartu.querySelector('h3 a')?.textContent.trim() || 'Produk Albis Antique',
        harga,
        gambar: kartu.dataset.image || kartu.querySelector('img')?.src || '',
        kategori: kartu.dataset.category || '',
        asal: kartu.dataset.origin || '',
        url: kartu.dataset.detailUrl || kartu.querySelector('h3 a')?.href || '#',
    };
}
function elemen(tag, kelas, teks) {
    const node = document.createElement(tag);
    if (kelas) node.className = kelas;
    if (teks !== undefined) node.textContent = teks;
    return node;
}
function formatRupiah(nilai) {
    return `Rp${Number(nilai || 0).toLocaleString('id-ID')}`;
}
function buatItemTersimpan(produk, mode) {
    const item = elemen('article', 'saved-item');
    const gambarLink = elemen('a', 'saved-item-image');
    gambarLink.href = produk.url || '#';
    if (produk.gambar) {
        const img = document.createElement('img');
        img.src = produk.gambar; img.alt = produk.nama || 'Foto produk'; img.loading = 'lazy';
        gambarLink.append(img);
    } else gambarLink.append(elemen('span', '', '✧'));
    const isi = elemen('div', 'saved-item-info');
    const meta = elemen('p', 'saved-item-meta', [produk.kategori, produk.asal].filter(Boolean).join(' · ') || 'Koleksi Albis Antique');
    const judul = elemen('h3');
    const tautan = elemen('a', '', produk.nama || 'Produk Albis Antique'); tautan.href = produk.url || '#'; judul.append(tautan);
    const harga = elemen('strong', 'saved-item-price', formatRupiah(produk.harga));
    isi.append(meta, judul, harga);
    item.append(gambarLink, isi);
    if (mode === 'cart') {
        const aksi = elemen('div', 'saved-item-actions');
        const jumlah = elemen('div', 'quantity-control');
        const kurang = elemen('button', '', '−'); kurang.type = 'button'; kurang.setAttribute('aria-label', 'Kurangi jumlah');
        const angka = elemen('span', '', String(produk.jumlah || 1));
        const tambah = elemen('button', '', '+'); tambah.type = 'button'; tambah.setAttribute('aria-label', 'Tambah jumlah');
        kurang.addEventListener('click', () => window.albisCart.ubahJumlah(produk.id, -1));
        tambah.addEventListener('click', () => window.albisCart.ubahJumlah(produk.id, 1));
        jumlah.append(kurang, angka, tambah);
        const subtotal = elemen('span', 'saved-item-subtotal', formatRupiah(Number(produk.harga || 0) * Number(produk.jumlah || 1)));
        const hapus = elemen('button', 'saved-remove', 'Hapus'); hapus.type = 'button';
        hapus.addEventListener('click', () => window.albisCart.hapus(produk.id));
        aksi.append(jumlah, subtotal, hapus);
        item.append(aksi);
    } else {
        const aksi = elemen('div', 'saved-item-actions');
        const pindah = elemen('button', 'button button-primary button-small', 'Tambah ke keranjang');
        pindah.type = 'button';
        pindah.addEventListener('click', () => {
            window.albisCart.tambahProduk(produk.id, produk);
            simpanWishlist(ambilWishlist().filter(item => Number(item.id) !== Number(produk.id)));
            renderWishlist(ambilWishlist());
            tampilkanToast('Produk dipindahkan ke keranjang');
        });
        const hapus = elemen('button', 'saved-remove', 'Hapus'); hapus.type = 'button';
        hapus.addEventListener('click', () => {
            simpanWishlist(ambilWishlist().filter(item => Number(item.id) !== Number(produk.id)));
            renderWishlist(ambilWishlist());
        });
        aksi.append(pindah, hapus); item.append(aksi);
    }
    return item;
}
function renderKeranjang(data = window.albisCart?.ambilData() || []) {
    const wadah = document.getElementById('cartContents');
    if (!wadah) return;
    wadah.replaceChildren();
    if (!data.length) {
        const kosong = elemen('div', 'saved-empty');
        kosong.append(elemen('div', 'saved-empty-icon', '🛍'), elemen('h2', '', 'Keranjang Anda masih kosong.'), elemen('p', '', 'Temukan benda antik yang ingin kamu bawa pulang.'));
        const link = elemen('a', 'button button-primary', 'Lanjut Belanja'); link.href = wadah.dataset.catalogUrl || '/katalog';
        kosong.append(link); wadah.append(kosong); return;
    }
    const daftar = elemen('div', 'saved-item-list');
    data.forEach(produk => daftar.append(buatItemTersimpan(produk, 'cart')));
    const ringkasan = elemen('div', 'saved-summary');
    const totalItem = data.reduce((n, p) => n + Number(p.jumlah || 1), 0);
    const totalHarga = data.reduce((n, p) => n + Number(p.harga || 0) * Number(p.jumlah || 1), 0);
    ringkasan.append(elemen('span', '', `${totalItem} item`), elemen('strong', '', `Total sementara: ${formatRupiah(totalHarga)}`));
    const checkout = elemen('a', 'button button-primary', 'Lanjut ke checkout'); checkout.href = wadah.dataset.checkoutUrl || '/customer/checkout';
    ringkasan.append(checkout); wadah.append(daftar, ringkasan);
}
function renderWishlist(data = ambilWishlist()) {
    const wadah = document.getElementById('wishlistContents');
    if (!wadah) return;
    wadah.replaceChildren();
    if (!data.length) {
        const kosong = elemen('div', 'saved-empty');
        kosong.append(elemen('div', 'saved-empty-icon', '♡'), elemen('h3', '', 'Belum ada item tersimpan.'), elemen('p', '', 'Simpan koleksi favoritmu dari katalog untuk menemukannya kembali di sini.'));
        const link = elemen('a', 'button button-primary', 'Jelajahi Katalog'); link.href = wadah.dataset.catalogUrl || '/katalog';
        kosong.append(link); wadah.append(kosong); return;
    }
    const daftar = elemen('div', 'saved-item-list');
    data.forEach(produk => daftar.append(buatItemTersimpan(produk, 'wishlist')));
    wadah.append(daftar);
}
/* ===== FUNGSI: INISIALISASI NAVIGASI RESPONSIF ===== */
function inisialisasiNavigasi() {
    const tombol = document.getElementById('mobileMenuButton');
    const menu = document.getElementById('navLinks');
    if (!tombol || !menu) return;

    tombol.addEventListener('click', () => {
        const terbuka = menu.classList.toggle('is-open');
        tombol.setAttribute('aria-expanded', String(terbuka));
        document.body.classList.toggle('menu-terbuka', terbuka);
    });

    menu.querySelectorAll('a').forEach((tautan) =>
        tautan.addEventListener('click', () => {
            menu.classList.remove('is-open');
            tombol.setAttribute('aria-expanded', 'false');
            document.body.classList.remove('menu-terbuka');
        }),
    );
}

/* ===== FUNGSI: INISIALISASI FILTER MOBILE ===== */
function inisialisasiFilterMobile() {
    const tombol = document.getElementById('filterMobileToggle');
    const panel = document.getElementById('filterPanel');
    tombol?.addEventListener('click', () => panel?.classList.toggle('is-open'));
}

/* ===== INISIALISASI HALAMAN ===== */
document.addEventListener('DOMContentLoaded', () => {
    /* Pesan server tampil sebagai toast ringkas di kanan atas. */
    document.querySelectorAll('.flash-wrapper .flash-message').forEach((pesan, indeks) => {
        window.setTimeout(() => {
            pesan.classList.add('is-dismissing');
            window.setTimeout(() => {
                pesan.remove();
                const wrapper = document.querySelector('.flash-wrapper');
                if (wrapper && !wrapper.querySelector('.flash-message')) wrapper.remove();
            }, 220);
        }, 5200 + indeks * 250);
    });
    const bahasa = new window.PengelolaBahasa();
    bahasa.terapkanBahasa();

    /* ===== EFEK KETIK PADA JUDUL HERO ===== */
    const hero = document.querySelector('.hero');
    const judulKetik = document.querySelector('[data-ketik]');
    const kurangGerak = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (hero && judulKetik && !kurangGerak) hero.classList.add('hero-menunggu');
    const tandaiHeroSiap = () => {
        hero?.classList.remove('hero-menunggu');
        hero?.classList.add('hero-siap');
    };

    const efekKetik = new window.EfekKetik(judulKetik, { saatSelesai: tandaiHeroSiap });
    efekKetik.mulai();
    window.setTimeout(tandaiHeroSiap, 6000); /* pengaman: bagian hero lain pasti muncul */

    document.getElementById('languageToggle')?.addEventListener('click', () => {
        bahasa.gantiBahasa();
        efekKetik.ulangi();
    });

    /* ===== EFEK MUNCUL SAAT SCROLL ===== */
    new window.EfekMuncul().pasang();

    const salju = new window.EfekSalju(document.getElementById('snowfall'));
    salju.mulai();

    inisialisasiNavigasi();
    inisialisasiFilterMobile();

    const keranjang = new KeranjangPrototype();
    window.albisCart = keranjang;
    keranjang.perbaruiBadge();
    perbaruiWishlistBadge();
    renderKeranjang(keranjang.ambilData());
    renderWishlist(ambilWishlist());
    document.querySelectorAll('[data-add-cart]').forEach((tombol) => {
        tombol.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (document.body.dataset.authenticated !== 'true') {
                tampilkanPromptLogin('cart');
                return;
            }
            keranjang.tambahProduk(Number(tombol.dataset.addCart), ambilDetailProduk(tombol));
            tombol.classList.add('is-ditambah');
            tombol.setAttribute('aria-pressed', 'true');
            window.setTimeout(() => {
                tombol.classList.remove('is-ditambah');
                tombol.setAttribute('aria-pressed', 'false');
            }, 900);
            tampilkanToast('Produk ditambahkan ke keranjang');
        });
    });

    /* Wishlist visual feedback: interaksi UI ringan tanpa mengubah backend. */
    document.querySelectorAll('.product-actions-float button[aria-label*="wishlist" i]').forEach((tombol) => {
        const id = Number(tombol.closest('[data-product]')?.dataset.id);
        const aktifAwal = ambilWishlist().some(item => Number(item.id) === id);
        tombol.classList.toggle('is-favorit', aktifAwal);
        tombol.setAttribute('aria-pressed', String(aktifAwal));
        tombol.textContent = aktifAwal ? '♥' : '♡';
        tombol.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (document.body.dataset.authenticated !== 'true') {
                tampilkanPromptLogin('wishlist');
                return;
            }
            const produk = ambilDetailProduk(tombol);
            const tersimpan = ambilWishlist();
            const ada = tersimpan.some(item => Number(item.id) === Number(produk.id));
            const terbaru = ada
                ? tersimpan.filter(item => Number(item.id) !== Number(produk.id))
                : [...tersimpan, produk];
            simpanWishlist(terbaru);
            const aktif = !ada;
            tombol.classList.toggle('is-favorit', aktif);
            tombol.setAttribute('aria-pressed', String(aktif));
            tombol.textContent = aktif ? '♥' : '♡';
            tampilkanToast(aktif ? 'Ditambahkan ke wishlist' : 'Dihapus dari wishlist');
        });
    });

    /* Aksi detail yang membutuhkan akun: tampilkan prompt yang sama. */
    document.querySelectorAll('[data-auth-action="wishlist"], [data-auth-action="cart"]').forEach((tombol) => {
        if (tombol.matches('.product-actions-float button')) return; /* sudah ditangani di atas */
        tombol.addEventListener('click', (event) => {
            if (document.body.dataset.authenticated !== 'true') {
                event.preventDefault();
                event.stopPropagation();
                tampilkanPromptLogin(tombol.dataset.authAction);
                return;
            }
            if (tombol.dataset.authAction === 'wishlist') {
                event.preventDefault();
                event.stopPropagation();
                const produk = ambilDetailProduk(tombol);
                if (!Number.isFinite(produk.id)) return;
                const lama = ambilWishlist();
                const ada = lama.some(item => Number(item.id) === Number(produk.id));
                simpanWishlist(ada
                    ? lama.filter(item => Number(item.id) !== Number(produk.id))
                    : [...lama, produk]);
                tombol.classList.toggle('is-favorit', !ada);
                tombol.setAttribute('aria-pressed', String(!ada));
                tampilkanToast(ada ? 'Dihapus dari wishlist' : 'Ditambahkan ke wishlist');
            }
        });
    });

    /* Zoom foto detail dalam lightbox sederhana. */
    document.querySelectorAll('[data-image-zoom]').forEach((tombol) => {
        tombol.addEventListener('click', () => {
            const gambar = tombol.querySelector('img');
            if (!gambar) return;
            const modal = document.createElement('div');
            modal.className = 'albis-lightbox';
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');
            modal.setAttribute('aria-label', 'Foto produk diperbesar');
            modal.innerHTML = '<button class="lightbox-close" type="button" aria-label="Tutup foto">×</button>';
            const salinan = gambar.cloneNode();
            salinan.removeAttribute('class');
            modal.append(salinan);
            document.body.append(modal);
            document.body.classList.add('lightbox-terbuka');
            const tutup = () => { modal.remove(); document.body.classList.remove('lightbox-terbuka'); document.removeEventListener('keydown', tombolEscape); tombol.focus(); };
            const tombolEscape = (event) => { if (event.key === 'Escape') tutup(); };
            modal.addEventListener('click', (event) => { if (event.target === modal || event.target.closest('.lightbox-close')) tutup(); });
            document.addEventListener('keydown', tombolEscape);
            modal.querySelector('.lightbox-close').focus();
        });
    });

    if (window.FilterKatalog && document.getElementById('catalogGrid')) {
        new window.FilterKatalog().pasang();
    }
});
