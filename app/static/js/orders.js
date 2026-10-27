'use strict';

/* Riwayat pesanan customer: data dari /customer/api/orders, bukti bayar dan ulasan lewat API. */
document.addEventListener('DOMContentLoaded', () => {
    const list = document.getElementById('orderList');
    if (!list || document.body.dataset.userRole !== 'customer') return;

    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
    const money = value => `Rp${Number(value || 0).toLocaleString('id-ID')}`;
    const tag = (name, cls = '', text = undefined) => {
        const node = document.createElement(name);
        if (cls) node.className = cls;
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const info = { ...list.dataset };
    const buttons = [...document.querySelectorAll('[data-order-filter]')];
    let filter = 'all';
    let orders = [];

    async function request(url, options = {}) {
        const headers = { Accept: 'application/json', ...(options.headers || {}) };
        if ((options.method || 'GET') !== 'GET') headers['X-CSRFToken'] = csrf;
        const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
        const body = await response.json().catch(() => ({}));
        if (response.status === 401) { window.location.href = body.login || '/auth/login'; throw new Error(body.error || 'Sesi berakhir.'); }
        if (!response.ok) throw new Error(body.error || `Permintaan gagal (${response.status}).`);
        return body;
    }

    async function muat() {
        try { orders = await request('/customer/api/orders'); render(); }
        catch (error) { list.replaceChildren(tag('div', 'account-empty-state', error.message)); }
    }

    function kotakMidtrans(order) {
        const box = tag('div', 'order-payment-info');
        box.append(tag('strong', '', `Total yang harus dibayar: ${money(order.total)}`));
        box.append(tag('p', '', 'Bayar aman lewat halaman Midtrans (VA bank, QRIS, e-wallet, kartu). Pesanan otomatis diproses setelah pembayaran berhasil.'));
        const catatan = tag('small', 'field-hint', '');
        const tombol = tag('button', 'button button-primary button-small', 'Bayar sekarang');
        tombol.type = 'button';
        tombol.addEventListener('click', async () => {
            tombol.disabled = true; catatan.textContent = 'Menyiapkan halaman pembayaran…';
            try {
                const hasil = await request(`/customer/api/orders/${order.id}/midtrans`, { method: 'POST' });
                if (!String(hasil.redirectUrl || '').startsWith('https://')) throw new Error('Alamat pembayaran tidak valid.');
                window.location.assign(hasil.redirectUrl);
            } catch (error) { catatan.textContent = error.message; tombol.disabled = false; }
        });
        box.append(tombol, catatan);
        const batas = new Date(order.batasBayar);
        if (!Number.isNaN(batas.getTime())) box.append(tag('small', 'field-hint', `Bayar sebelum ${batas.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })}.`));
        return box;
    }

    async function sinkronSetelahKembali() {
        if (new URLSearchParams(window.location.search).get('midtrans') !== 'selesai') return;
        const pending = orders.filter(o => o.pembayaran === 'Midtrans' && o.status === 'Menunggu pembayaran');
        for (const o of pending) { try { await request(`/customer/api/orders/${o.id}/midtrans/sinkron`, { method: 'POST' }); } catch (_) { /* webhook akan menyusul */ } }
        window.history.replaceState(null, '', window.location.pathname);
        if (pending.length) await muat();
    }

    function formUlasan(item) {
        const wrap = tag('div', 'order-review');
        const saya = item.ulasanSaya;
        if (saya) {
            wrap.append(tag('strong', 'order-review-submitted', 'Ulasan sudah dikirim'));
            wrap.append(tag('p', '', `${'★'.repeat(Number(saya.rating || 0))}${'☆'.repeat(5 - Number(saya.rating || 0))}${saya.komentar ? ` · ${saya.komentar}` : ''}`));
            if (saya.gambar_url) {
                const link = tag('a', 'order-review-photo-link'); link.href = saya.gambar_url; link.target = '_blank'; link.rel = 'noopener noreferrer';
                const img = tag('img', 'order-review-photo'); img.src = saya.gambar_url; img.alt = `Foto ulasan ${item.nama}`; img.loading = 'lazy'; link.append(img); wrap.append(link);
            }
            if (saya.tersembunyi) wrap.append(tag('small', 'field-hint', 'Ulasanmu saat ini disembunyikan oleh admin.'));
            return wrap;
        }
        const toggle = tag('button', 'button button-secondary button-small', 'Tulis ulasan');
        toggle.type = 'button';
        const form = tag('div', 'order-review-form'); form.hidden = true;
        const select = tag('select', 'form-control'); select.setAttribute('aria-label', `Rating untuk ${item.nama}`);
        for (let n = 5; n >= 1; n -= 1) { const o = tag('option', '', `${'★'.repeat(n)}${'☆'.repeat(5 - n)} (${n})`); o.value = String(n); select.append(o); }
        const area = tag('textarea', 'form-control'); area.maxLength = 1000; area.rows = 3;
        area.placeholder = 'Ceritakan kondisi barang dan pengalamanmu (opsional)';
        const fileLabel = tag('label', 'order-review-file-label', 'Lampirkan foto (opsional)');
        const fileInput = document.createElement('input'); fileInput.type = 'file'; fileInput.accept = 'image/jpeg,image/png,image/webp'; fileInput.setAttribute('aria-label', 'Foto untuk ulasan');
        const note = tag('small', 'field-hint', 'JPG, PNG, WEBP maksimal 3 MB. Batas waktu ulasan: 7 hari setelah pesanan selesai; setiap produk hanya bisa diulas sekali.');
        fileInput.addEventListener('change', () => {
            const file = fileInput.files?.[0];
            if (file && (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 3 * 1024 * 1024)) {
                fileInput.value = ''; note.textContent = 'Pilih foto JPG, PNG, atau WEBP maksimal 3 MB.';
            }
        });
        const kirim = tag('button', 'button button-primary button-small', 'Kirim ulasan'); kirim.type = 'button';
        toggle.addEventListener('click', () => { form.hidden = !form.hidden; });
        kirim.addEventListener('click', async () => {
            const data = new FormData(); data.append('product_id', String(item.id)); data.append('rating', select.value); data.append('komentar', area.value);
            const file = fileInput.files?.[0]; if (file) data.append('gambarUlasan', file);
            kirim.disabled = true; note.textContent = 'Mengirim ulasan…';
            try { await request('/customer/api/reviews', { method: 'POST', body: data }); await muat(); }
            catch (error) { note.textContent = error.message; kirim.disabled = false; }
        });
        fileLabel.append(fileInput);
        form.append(select, area, fileLabel, kirim, note);
        wrap.append(toggle, form);
        return wrap;
    }

    function render() {
        list.replaceChildren();
        const rows = orders.filter(order => filter === 'all' || order.status === filter);
        if (!rows.length) {
            const empty = tag('div', 'account-empty-state', filter === 'all' ? 'Belum ada pesanan pada akun ini.' : 'Tidak ada pesanan dengan status tersebut.');
            const link = tag('a', '', 'Jelajahi katalog →'); link.href = '/katalog'; empty.append(link);
            list.append(empty); return;
        }
        rows.forEach(order => {
            const card = tag('article', 'order-card'); card.dataset.orderStatus = order.status;
            const top = tag('div', 'order-card-top');
            const meta = tag('div');
            meta.append(tag('span', 'order-number', `ORDER ${order.orderNumber}`),
                tag('span', 'order-date', new Date(order.date).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })));
            top.append(meta, tag('span', `order-status ${order.status === 'Selesai' ? 'is-complete' : 'is-processing'}`, order.status));

            const items = tag('div', 'order-items');
            (order.items || []).forEach(item => {
                const row = tag('div', 'order-product');
                const visual = tag('div', 'order-product-visual'); visual.setAttribute('aria-hidden', 'true');
                if (item.gambar) { const foto = tag('img'); foto.src = item.gambar; foto.alt = ''; foto.loading = 'lazy'; foto.referrerPolicy = 'no-referrer'; visual.append(foto); }
                else visual.textContent = 'Foto belum tersedia';
                const copy = tag('div', 'order-product-copy');
                const title = tag('h3');
                if (item.id) { const a = tag('a', '', item.nama); a.href = `/produk/${item.id}`; title.append(a); } else title.textContent = item.nama;
                copy.append(title, tag('p', '', `${item.jumlah} × ${money(item.harga)}`));
                row.append(visual, copy, tag('strong', '', money(Number(item.harga) * Number(item.jumlah))));
                items.append(row);
                if (item.bisaUlas || item.ulasanSaya) items.append(formUlasan(item));
            });

            const bottom = tag('div', 'order-card-bottom');
            bottom.append(tag('span', '', `Total ${money(order.total)}${order.ongkir > 0 ? ` (termasuk ongkir ${money(order.ongkir)})` : ''} · ${order.pembayaran}`));
            bottom.append(tag('span', '', `Penerima: ${order.nama} · ${order.alamat || ''}`));
            card.append(top, items, bottom);
            if (order.status === 'Menunggu pembayaran') {
                const batal = tag('button', 'button button-secondary button-small', 'Batalkan pesanan');
                batal.type = 'button';
                batal.addEventListener('click', async () => {
                    if (!window.confirm(`Batalkan pesanan ${order.orderNumber}? Stok akan dikembalikan.`)) return;
                    batal.disabled = true;
                    try { await request(`/customer/api/orders/${order.id}/batal`, { method: 'POST' }); await muat(); }
                    catch (error) { batal.disabled = false; window.alert(error.message); }
                });
                card.append(batal);
            }

            const bukti = order.buktiBayar;
            if (bukti) {
                const state = tag('span', 'order-proof-state', `Bukti bayar: ${bukti.status}`);
                const link = tag('a', 'table-footnote', ` ${bukti.namaFile}`); link.href = bukti.url; link.target = '_blank'; link.rel = 'noopener';
                state.append(link); bottom.append(state);
                if (bukti.status === 'Ditolak') card.append(tag('p', 'order-rejected-note', `Bukti ditolak admin: ${bukti.catatan || 'tidak sesuai'}. Silakan unggah ulang.`));
            }
            if (order.status === 'Menunggu pembayaran' && order.pembayaran === 'Midtrans') card.append(kotakMidtrans(order));
            else if (order.status === 'Menunggu pembayaran') card.append(tag('p', 'order-payment-info', 'Metode pembayaran pada pesanan lama tidak lagi tersedia. Hubungi admin jika kamu memerlukan bantuan.'));
            list.append(card);
        });
    }

    buttons.forEach(button => button.addEventListener('click', () => {
        filter = button.dataset.orderFilter;
        buttons.forEach(node => node.classList.toggle('is-active', node === button));
        render();
    }));
    muat().then(sinkronSetelahKembali);
});
