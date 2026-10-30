'use strict';

const albisBody = document.body;
const albisIsCustomer = () => albisBody.dataset.userRole === 'customer' && Boolean(albisBody.dataset.userId);

function inisialisasiProfilNavbar() {
    const tautan = document.querySelector('[data-nav-profile]');
    if (!tautan || !albisIsCustomer()) return;

    const namaNode = document.getElementById('navProfileName');
    const fotoNode = document.getElementById('navProfileImage');
    const fallbackNode = document.getElementById('navProfileFallback');
    let profil = { nama: albisBody.dataset.userName || '', foto: albisBody.dataset.userAvatar || '' };

    const sinkronkan = () => {
        const nama = typeof profil.nama === 'string' && profil.nama.trim()
            ? profil.nama.trim() : (albisBody.dataset.userName || 'Akun Saya');
        if (namaNode) namaNode.textContent = nama;
        tautan.setAttribute('aria-label', `Akun ${nama}`);
        tautan.title = `Akun ${nama}`;
        const foto = typeof profil.foto === 'string' && profil.foto.startsWith('data:image/') ? profil.foto : '';
        if (fotoNode && foto) {
            fotoNode.src = foto; fotoNode.hidden = false;
            if (fallbackNode) fallbackNode.hidden = true;
        } else {
            if (fotoNode) { fotoNode.removeAttribute('src'); fotoNode.hidden = true; }
            if (fallbackNode) fallbackNode.hidden = false;
        }
    };

    sinkronkan();
    window.addEventListener('albis:profile-updated', event => {
        if (event.detail) profil = event.detail;
        sinkronkan();
    });
}

function tampilkanPromptLogin() {
    if (document.querySelector('.albis-auth-prompt')) return;
    const overlay = document.createElement('div');
    overlay.className = 'albis-auth-prompt';
    overlay.setAttribute('role', 'presentation');
    overlay.innerHTML = `
        <section class="albis-auth-dialog" role="dialog" aria-modal="true" aria-labelledby="albisAuthTitle" aria-describedby="albisAuthDescription">
            <button class="albis-auth-close" type="button" aria-label="Tutup dialog">×</button>
            <div class="albis-auth-crest" aria-hidden="true">♔</div>
            <h2 id="albisAuthTitle">Masuk untuk melanjutkan</h2>
            <p id="albisAuthDescription">Masuk ke akun customer Albis Antique agar keranjang tersimpan khusus untuk akunmu.</p>
            <div class="albis-auth-actions">
                <button class="albis-auth-later" type="button">Nanti saja</button>
                <a class="albis-auth-login" href="${albisBody.dataset.loginUrl || '/auth/login'}"><img class="ui-icon button-leading-icon" src="${albisBody.dataset.loginIconUrl || '/static/images/icons/login.svg'}" alt="" aria-hidden="true">Masuk</a>
            </div>
        </section>`;
    document.body.append(overlay);
    document.body.classList.add('lightbox-terbuka');
    const tutup = () => {
        overlay.remove();
        document.body.classList.remove('lightbox-terbuka');
        document.removeEventListener('keydown', tombolEscape);
    };
    const tombolEscape = (event) => { if (event.key === 'Escape') tutup(); };
    overlay.addEventListener('click', event => {
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
    toast._timer = window.setTimeout(() => toast.classList.remove('is-visible'), 2600);
}

function formatRupiah(nilai) { return `Rp${Number(nilai || 0).toLocaleString('id-ID')}`; }
function elemen(tag, kelas, teks) {
    const node = document.createElement(tag);
    if (kelas) node.className = kelas;
    if (teks !== undefined) node.textContent = teks;
    return node;
}

/* Keranjang: seluruh data tersimpan di PostgreSQL lewat /customer/api/cart. */
class Keranjang {
    constructor() {
        this.userId = albisIsCustomer() ? albisBody.dataset.userId : '';
        this.data = [];
        this.ready = this.userId ? this.muatDariServer() : Promise.resolve([]);
    }
    async requestServer(url, method = 'GET', payload = undefined) {
        const headers = { Accept: 'application/json' };
        const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
        if (csrf) headers['X-CSRFToken'] = csrf;
        const options = { method, credentials: 'same-origin', headers };
        if (payload !== undefined) {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(payload);
        }
        const response = await fetch(url, options);
        const body = await response.json().catch(() => ({}));
        if (response.status === 401) { window.location.href = body.login || albisBody.dataset.loginUrl || '/auth/login'; throw new Error(body.error || 'Sesi berakhir.'); }
        if (!response.ok) throw new Error(body.error || `Permintaan keranjang gagal (${response.status}).`);
        return body;
    }
    terapkan(result) {
        this.data = (result.items || []).map(item => ({ ...item, url: `/produk/${item.id}`, dipilih: item.dipilih !== false }));
        this.perbaruiBadge();
        renderKeranjang(this.data);
    }
    async jalankan(url, method, payload, pesanGagal) {
        try { this.terapkan(await this.requestServer(url, method, payload)); return true; }
        catch (error) { tampilkanToast(error.message || pesanGagal); return false; }
    }
    async muatDariServer() {
        await this.jalankan('/customer/api/cart', 'GET', undefined, 'Keranjang tidak dapat dimuat.');
        return this.data;
    }
    tambahProduk(idProduk, jumlah = 1) {
        return this.jalankan('/customer/api/cart', 'POST', { product_id: Number(idProduk), quantity: Math.max(1, Number(jumlah || 1)) }, 'Produk gagal ditambahkan ke keranjang.');
    }
    ubahJumlah(idProduk, delta) {
        const item = this.data.find(row => Number(row.id) === Number(idProduk));
        if (!item) return Promise.resolve(false);
        const quantity = Number(item.jumlah || 1) + Number(delta);
        const url = `/customer/api/cart/${Number(idProduk)}`;
        return quantity <= 0
            ? this.jalankan(url, 'DELETE', undefined, 'Produk gagal dihapus.')
            : this.jalankan(url, 'PUT', { quantity }, 'Jumlah keranjang gagal diperbarui.');
    }
    aturPilihan(idProduk, dipilih) {
        return this.jalankan(`/customer/api/cart/${Number(idProduk)}`, 'PUT', { selected: Boolean(dipilih) }, 'Pilihan produk gagal disimpan.');
    }
    pilihSemua(dipilih) {
        return this.jalankan('/customer/api/cart/pilih-semua', 'PUT', { selected: Boolean(dipilih) }, 'Pilihan keranjang gagal disimpan.');
    }
    async hapus(idProduk) {
        if (await this.jalankan(`/customer/api/cart/${Number(idProduk)}`, 'DELETE', undefined, 'Produk gagal dihapus.')) tampilkanToast('Produk dihapus dari keranjang.');
    }
    ambilData() { return this.data.map(item => ({ ...item })); }
    perbaruiBadge() {
        const badge = document.getElementById('cartBadge');
        if (!badge) return;
        if (!albisIsCustomer()) { badge.textContent = '0'; badge.hidden = true; return; }
        const total = this.data.reduce((jumlah, item) => jumlah + Number(item.jumlah || 1), 0);
        badge.textContent = String(total);
        badge.hidden = total === 0;
    }
}

function ambilDetailProduk(tombol) {
    const kartu = tombol.closest('[data-product]');
    if (!kartu) {
        const quantity = Number(tombol.closest('.product-copy')?.querySelector('.quantity-control strong')?.textContent || 1);
        return {
            id: Number(tombol.dataset.productId || tombol.dataset.addCart),
            nama: tombol.dataset.productName || 'Produk Albis Antique',
            harga: Number(tombol.dataset.productPrice) || 0,
            gambar: tombol.dataset.productImage || '',
            kategori: tombol.dataset.productCategory || '',
            asal: tombol.dataset.productOrigin || '',
            stok: Number(tombol.dataset.productStock || 1),
            jumlah: quantity,
            url: tombol.dataset.productUrl || '',
        };
    }
    const hargaTeks = kartu.querySelector('.price')?.textContent || '';
    return {
        id: Number(kartu.dataset.id),
        nama: kartu.querySelector('h3 a')?.textContent.trim() || 'Produk Albis Antique',
        harga: Number(hargaTeks.replace(/[^0-9]/g, '')) || Number(kartu.dataset.price) || 0,
        gambar: kartu.dataset.image || kartu.querySelector('img')?.src || '',
        kategori: kartu.dataset.category || '',
        asal: kartu.dataset.origin || '',
        stok: Number(kartu.dataset.stock || 1),
        url: kartu.dataset.detailUrl || kartu.querySelector('h3 a')?.href || '#',
    };
}

function buatItemKeranjang(produk) {
    const item = elemen('article', 'saved-item cart-item');
    const pilihLabel = elemen('label', 'cart-item-check');
    const pilih = document.createElement('input');
    pilih.type = 'checkbox';
    pilih.checked = produk.dipilih !== false;
    pilih.setAttribute('aria-label', `Pilih ${produk.nama || 'produk'} untuk checkout`);
    pilih.addEventListener('change', () => window.albisCart.aturPilihan(produk.id, pilih.checked));
    pilihLabel.append(pilih);

    const gambarLink = elemen('a', 'saved-item-image');
    gambarLink.href = produk.url || '#';
    if (produk.gambar) {
        const img = document.createElement('img');
        img.src = produk.gambar; img.alt = produk.nama || 'Foto produk'; img.loading = 'lazy';
        gambarLink.append(img);
    } else gambarLink.append(elemen('span', '', '✧'));

    const isi = elemen('div', 'saved-item-info');
    isi.append(elemen('p', 'saved-item-meta', [produk.kategori, produk.asal].filter(Boolean).join(' · ') || 'Koleksi Albis Antique'));
    const judul = elemen('h3');
    const tautan = elemen('a', '', produk.nama || 'Produk Albis Antique'); tautan.href = produk.url || '#'; judul.append(tautan);
    isi.append(judul, elemen('strong', 'saved-item-price', formatRupiah(produk.harga)));

    const aksi = elemen('div', 'saved-item-actions');
    const jumlah = elemen('div', 'quantity-control');
    const kurang = elemen('button', '', '−'); kurang.type = 'button'; kurang.setAttribute('aria-label', `Kurangi jumlah ${produk.nama}`); kurang.disabled = Number(produk.jumlah || 1) <= 1;
    const angka = elemen('span', '', String(produk.jumlah || 1));
    const tambah = elemen('button', '', '+'); tambah.type = 'button'; tambah.setAttribute('aria-label', `Tambah jumlah ${produk.nama}`); tambah.disabled = Number(produk.jumlah || 1) >= Number(produk.stok || 1);
    kurang.addEventListener('click', () => window.albisCart.ubahJumlah(produk.id, -1));
    tambah.addEventListener('click', () => window.albisCart.ubahJumlah(produk.id, 1));
    jumlah.append(kurang, angka, tambah);
    aksi.append(jumlah, elemen('span', 'saved-item-subtotal', formatRupiah(Number(produk.harga || 0) * Number(produk.jumlah || 1))));
    const hapus = elemen('button', 'saved-remove', 'Hapus'); hapus.type = 'button';
    hapus.addEventListener('click', () => window.albisCart.hapus(produk.id));
    aksi.append(hapus);
    item.append(pilihLabel, gambarLink, isi, aksi);
    return item;
}

function renderKeranjang(data = window.albisCart?.ambilData() || []) {
    const wadah = document.getElementById('cartContents');
    if (!wadah) return;
    wadah.replaceChildren();
    if (!albisIsCustomer()) {
        const kosong = elemen('div', 'saved-empty');
        kosong.append(elemen('div', 'saved-empty-icon', '♙'), elemen('h2', '', 'Masuk untuk melihat keranjangmu'), elemen('p', '', 'Keranjang akan terikat pada akun customer setelah kamu masuk.'));
        const login = elemen('a', 'button button-primary', 'Masuk ke akun'); login.href = albisBody.dataset.loginUrl || '/auth/login';
        const catalog = elemen('a', 'button button-secondary', 'Jelajahi katalog'); catalog.href = wadah.dataset.catalogUrl || '/katalog';
        kosong.append(login, catalog); wadah.append(kosong); return;
    }
    if (!data.length) {
        const kosong = elemen('div', 'saved-empty');
        kosong.append(elemen('div', 'saved-empty-icon', '🛍'), elemen('h2', '', 'Keranjang Anda masih kosong.'), elemen('p', '', 'Temukan benda antik yang ingin kamu bawa pulang.'));
        const link = elemen('a', 'button button-primary', 'Lanjut Belanja'); link.href = wadah.dataset.catalogUrl || '/katalog';
        kosong.append(link); wadah.append(kosong); return;
    }

    const selected = data.filter(item => item.dipilih !== false);
    const controls = elemen('div', 'cart-selection-toolbar');
    const selectAllLabel = elemen('label', 'cart-select-all-label');
    const selectAll = document.createElement('input'); selectAll.type = 'checkbox';
    selectAll.checked = selected.length === data.length;
    selectAll.indeterminate = selected.length > 0 && selected.length < data.length;
    selectAll.setAttribute('aria-label', 'Pilih semua produk');
    selectAll.addEventListener('change', () => window.albisCart.pilihSemua(selectAll.checked));
    selectAllLabel.append(selectAll, document.createTextNode('Pilih semua'));
    controls.append(selectAllLabel, elemen('span', '', `${selected.length} dari ${data.length} produk dipilih`));

    const daftar = elemen('div', 'saved-item-list');
    data.forEach(produk => daftar.append(buatItemKeranjang(produk)));
    const ringkasan = elemen('div', 'saved-summary cart-summary');
    const totalKuantitas = selected.reduce((n, p) => n + Number(p.jumlah || 1), 0);
    const totalHarga = selected.reduce((n, p) => n + Number(p.harga || 0) * Number(p.jumlah || 1), 0);
    ringkasan.append(elemen('span', '', `${totalKuantitas} item dipilih`), elemen('strong', '', `Subtotal pilihan: ${formatRupiah(totalHarga)}`));
    const checkout = elemen('button', 'button button-primary', `Lanjut ke checkout (${selected.length})`);
    checkout.type = 'button'; checkout.disabled = selected.length === 0;
    checkout.addEventListener('click', () => {
        const ids = window.albisCart.ambilData().filter(item => item.dipilih !== false).map(item => Number(item.id));
        if (!ids.length) { tampilkanToast('Pilih minimal satu produk untuk checkout.'); return; }
        window.location.href = wadah.dataset.checkoutUrl || '/customer/checkout';
    });
    ringkasan.append(checkout);
    wadah.append(controls, daftar, ringkasan);
}

function inisialisasiNavigasi() {
    const tombol = document.getElementById('mobileMenuButton');
    const menu = document.getElementById('navLinks');
    if (!tombol || !menu) return;
    tombol.addEventListener('click', () => {
        const terbuka = menu.classList.toggle('is-open');
        tombol.setAttribute('aria-expanded', String(terbuka));
        document.body.classList.toggle('menu-terbuka', terbuka);
    });
    menu.querySelectorAll('a').forEach(tautan => tautan.addEventListener('click', () => {
        menu.classList.remove('is-open');
        tombol.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('menu-terbuka');
    }));
}
function inisialisasiFilterMobile() {
    const tombol = document.getElementById('filterMobileToggle');
    const panel = document.getElementById('filterPanel');
    tombol?.addEventListener('click', () => {
        const terbuka = panel?.classList.toggle('is-open');
        tombol.setAttribute('aria-expanded', String(Boolean(terbuka)));
    });
}
function inisialisasiKuantitasDetail() {
    document.querySelectorAll('.detail-cart-panel .quantity-control').forEach(control => {
        const minus = control.querySelector('[data-quantity-minus]');
        const plus = control.querySelector('[data-quantity-plus]');
        const angka = control.querySelector('[data-quantity-value]');
        const addButton = control.closest('.detail-cart-panel')?.querySelector('[data-add-cart]');
        if (!angka || !minus || !plus || !addButton) return;
        let quantity = 1;
        const max = () => Math.max(1, Number(addButton.dataset.productStock || 1));
        const render = () => { angka.textContent = String(quantity); minus.disabled = quantity <= 1; plus.disabled = quantity >= max(); };
        minus.addEventListener('click', () => { quantity = Math.max(1, quantity - 1); render(); });
        plus.addEventListener('click', () => { quantity = Math.min(max(), quantity + 1); render(); });
        render();
    });
}

/* ===== INISIALISASI HALAMAN ===== */
document.addEventListener('DOMContentLoaded', () => {
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

    const hero = document.querySelector('.hero');
    const judulKetik = document.querySelector('[data-ketik]');
    const kurangGerak = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (hero && judulKetik && !kurangGerak) hero.classList.add('hero-menunggu');
    const tandaiHeroSiap = () => { hero?.classList.remove('hero-menunggu'); hero?.classList.add('hero-siap'); };
    const efekKetik = new window.EfekKetik(judulKetik, { saatSelesai: tandaiHeroSiap });
    efekKetik.mulai();
    window.setTimeout(tandaiHeroSiap, 6000);
    new window.EfekMuncul().pasang();
    new window.EfekSalju(document.getElementById('snowfall')).mulai();
    inisialisasiNavigasi();
    inisialisasiFilterMobile();
    inisialisasiKuantitasDetail();
    inisialisasiProfilNavbar();

    const bukaPanelKeranjang = document.getElementById('detailOpenCart');
    const panelKeranjang = document.getElementById('detailCartPanel');
    const tutupPanelKeranjang = document.getElementById('detailCloseCart');
    const aturPanelKeranjang = (terbuka) => {
        if (!panelKeranjang || !bukaPanelKeranjang) return;
        panelKeranjang.hidden = !terbuka;
        bukaPanelKeranjang.setAttribute('aria-expanded', String(terbuka));
        if (terbuka) panelKeranjang.querySelector('[data-quantity-minus]')?.focus();
    };
    bukaPanelKeranjang?.addEventListener('click', () => {
        if (!albisIsCustomer()) {
            if (albisBody.dataset.userRole === 'admin') tampilkanToast('Keranjang hanya tersedia untuk akun customer.');
            else tampilkanPromptLogin();
            return;
        }
        aturPanelKeranjang(panelKeranjang?.hidden !== false);
    });
    tutupPanelKeranjang?.addEventListener('click', () => { aturPanelKeranjang(false); bukaPanelKeranjang?.focus(); });

    const keranjang = new Keranjang();
    window.albisCart = keranjang;
    keranjang.perbaruiBadge();
    if (!albisIsCustomer()) renderKeranjang([]);

    // Delegasi event agar kartu produk apa pun tetap interaktif.
    document.addEventListener('click', async event => {
        const target = event.target instanceof Element ? event.target : event.target?.parentElement;
        if (!target) return;

        // Prioritaskan Beli Sekarang jika tombol juga memiliki data-product-id / data-add-cart.
        const tombolBeli = target.closest('[data-buy-now]');
        if (tombolBeli) {
            event.preventDefault(); event.stopPropagation();
            if (!albisIsCustomer()) {
                if (albisBody.dataset.userRole === 'admin') { tampilkanToast('Fitur belanja hanya tersedia untuk akun customer.'); return; }
                tampilkanPromptLogin(); return;
            }
            const produk = ambilDetailProduk(tombolBeli);
            const quantity = Number(tombolBeli.closest('.product-copy')?.querySelector('[data-quantity-value]')?.textContent || 1);
            const stok = Math.max(0, Number(produk.stok || 0));
            if (stok < 1) { tampilkanToast('Stok produk sedang habis.'); return; }
            const safeQuantity = Math.min(stok, Math.max(1, quantity));
            window.location.href = `${tombolBeli.dataset.checkoutUrl || '/customer/checkout'}?direct_product_id=${encodeURIComponent(produk.id)}&quantity=${encodeURIComponent(safeQuantity)}`;
            return;
        }

        const tombol = target.closest('[data-add-cart]');
        if (!tombol) {
            const tombolAuth = target.closest('[data-auth-action="cart"]');
            if (tombolAuth && !albisIsCustomer()) {
                event.preventDefault(); event.stopPropagation();
                if (albisBody.dataset.userRole === 'admin') tampilkanToast('Keranjang hanya tersedia untuk akun customer.');
                else tampilkanPromptLogin();
            }
            return;
        }

        event.preventDefault(); event.stopPropagation();
        if (!albisIsCustomer()) {
            if (albisBody.dataset.userRole === 'admin') { tampilkanToast('Keranjang hanya tersedia untuk akun customer.'); return; }
            tampilkanPromptLogin(); return;
        }
        const quantity = Number(tombol.closest('.detail-cart-panel')?.querySelector('[data-quantity-value]')?.textContent || 1);
        if (await keranjang.tambahProduk(Number(tombol.dataset.addCart), quantity)) {
            tombol.classList.add('is-ditambah'); tombol.setAttribute('aria-pressed', 'true');
            window.setTimeout(() => { tombol.classList.remove('is-ditambah'); tombol.setAttribute('aria-pressed', 'false'); }, 900);
            tampilkanToast('Produk ditambahkan ke keranjang akunmu.');
            aturPanelKeranjang(false);
        }
    });

    document.querySelectorAll('[data-image-zoom]').forEach(tombol => tombol.addEventListener('click', () => {
        const gambar = tombol.querySelector('img');
        if (!gambar) return;
        const modal = document.createElement('div');
        modal.className = 'albis-lightbox'; modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true'); modal.setAttribute('aria-label', 'Foto produk diperbesar');
        modal.innerHTML = '<button class="lightbox-close" type="button" aria-label="Tutup foto">×</button>';
        const salinan = gambar.cloneNode(); salinan.removeAttribute('class'); modal.append(salinan); document.body.append(modal); document.body.classList.add('lightbox-terbuka');
        const tutup = () => { modal.remove(); document.body.classList.remove('lightbox-terbuka'); document.removeEventListener('keydown', tombolEscape); tombol.focus(); };
        const tombolEscape = event => { if (event.key === 'Escape') tutup(); };
        modal.addEventListener('click', event => { if (event.target === modal || event.target.closest('.lightbox-close')) tutup(); });
        document.addEventListener('keydown', tombolEscape); modal.querySelector('.lightbox-close').focus();
    }));

    if (window.FilterKatalog && document.getElementById('catalogGrid')) {
        window.albisFilterKatalog = new window.FilterKatalog();
        window.albisFilterKatalog.pasang();
    }
});

/* ===== Pengganti atribut onerror/inline script (CSP: script-src 'self') ===== */
document.addEventListener('error', event => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement)) return;
    if (img.dataset.imgFallback === 'remove') img.remove();
    else if (img.dataset.imgFallback === 'class') { img.classList.add('is-fallback'); img.removeAttribute('src'); }
}, true);

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.workspace-mobile-toggle').forEach(button => {
        const sidebar = document.getElementById(button.getAttribute('aria-controls') || '');
        if (!sidebar) return;
        const tutup = () => { sidebar.classList.remove('is-open'); button.setAttribute('aria-expanded', 'false'); };
        button.addEventListener('click', () => button.setAttribute('aria-expanded', String(sidebar.classList.toggle('is-open'))));
        sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', tutup));
        document.addEventListener('keydown', event => { if (event.key === 'Escape') tutup(); });
    });
    const lupa = document.getElementById('forgotPasswordButton');
    const info = document.getElementById('forgotPasswordInfo');
    lupa?.addEventListener('click', () => {
        const buka = info.hidden; info.hidden = !buka; lupa.setAttribute('aria-expanded', String(buka));
    });
});
