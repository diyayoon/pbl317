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

    function kotakInstruksi(order) {
        const box = tag('div', 'order-payment-info');
        box.append(tag('strong', '', `Total yang harus dibayar: ${money(order.total)}`));
        const batas = new Date(order.batasBayar);
        if (order.pembayaran === 'QRIS') {
            box.append(tag('p', '', info.qris || 'Hubungi admin Albis Antique untuk mendapatkan kode QRIS pembayaran.'));
        } else if (info.rekening) {
            box.append(tag('p', '', `Transfer ke ${info.bank || 'rekening toko'} ${info.rekening}${info.atasNama ? ` a.n. ${info.atasNama}` : ''}.`));
        } else {
            box.append(tag('p', '', 'Hubungi admin Albis Antique untuk mendapatkan nomor rekening pembayaran.'));
        }
        if (!Number.isNaN(batas.getTime())) {
            box.append(tag('small', 'field-hint', `Bayar sebelum ${batas.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })}; pesanan otomatis dibatalkan setelah itu.`));
        }
        return box;
    }

    function formUnggah(order, ulang) {
        const box = tag('div', 'order-proof-upload');
        const label = tag('label', '', ulang ? 'Unggah ulang bukti pembayaran' : 'Unggah bukti pembayaran');
        const input = document.createElement('input');
        input.type = 'file'; input.accept = 'image/jpeg,image/png,image/webp,application/pdf';
        input.setAttribute('aria-label', 'Pilih file bukti pembayaran');
        const note = tag('small', 'field-hint', 'JPG, PNG, WEBP, atau PDF — maksimal 5 MB.');
        const action = tag('button', 'button button-primary button-small', 'Kirim bukti');
        action.type = 'button'; action.disabled = true;
        input.addEventListener('change', () => {
            const file = input.files?.[0];
            action.disabled = !file;
            if (file && (file.size > 5 * 1024 * 1024 || !['image/jpeg', 'image/png', 'image/webp', 'application/pdf'].includes(file.type))) {
                input.value = ''; action.disabled = true; note.textContent = 'Gunakan JPG, PNG, WEBP, atau PDF maksimal 5 MB.';
            } else if (file) note.textContent = `${file.name} siap dikirim.`;
        });
        action.addEventListener('click', async () => {
            const file = input.files?.[0]; if (!file) return;
            const data = new FormData(); data.append('buktiBayar', file);
            action.disabled = true; note.textContent = 'Mengunggah bukti pembayaran…';
            try { await request(`/customer/api/orders/${order.id}/bukti`, { method: 'POST', body: data }); await muat(); }
            catch (error) { note.textContent = error.message; action.disabled = false; }
        });
        label.append(input);
        box.append(label, note, action);
        return box;
    }

    function formUlasan(item) {
        const wrap = tag('div', 'order-review');
        const saya = item.ulasanSaya;
        const toggle = tag('button', 'button button-secondary button-small', saya ? 'Ubah ulasan' : 'Tulis ulasan');
        toggle.type = 'button';
        const form = tag('div', 'order-review-form'); form.hidden = true;
        const select = tag('select', 'form-control');
        select.setAttribute('aria-label', `Rating untuk ${item.nama}`);
        for (let n = 5; n >= 1; n -= 1) { const o = tag('option', '', `${'★'.repeat(n)}${'☆'.repeat(5 - n)} (${n})`); o.value = String(n); select.append(o); }
        if (saya) select.value = String(saya.rating);
        const area = tag('textarea', 'form-control'); area.maxLength = 1000; area.rows = 3;
        area.placeholder = 'Ceritakan kondisi barang dan pengalamanmu (opsional)'; area.value = saya?.komentar || '';
        const kirim = tag('button', 'button button-primary button-small', 'Simpan ulasan'); kirim.type = 'button';
        const note = tag('small', 'field-hint', saya?.tersembunyi ? 'Ulasanmu disembunyikan oleh admin.' : '');
        toggle.addEventListener('click', () => { form.hidden = !form.hidden; });
        kirim.addEventListener('click', async () => {
            kirim.disabled = true;
            try {
                await request('/customer/api/reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: item.id, rating: Number(select.value), komentar: area.value }) });
                await muat();
            } catch (error) { note.textContent = error.message; kirim.disabled = false; }
        });
        form.append(select, area, kirim, note);
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
                const visual = tag('div', 'order-product-visual', '♜'); visual.setAttribute('aria-hidden', 'true');
                const copy = tag('div', 'order-product-copy');
                const title = tag('h3');
                if (item.id) { const a = tag('a', '', item.nama); a.href = `/produk/${item.id}`; title.append(a); } else title.textContent = item.nama;
                copy.append(title, tag('p', '', `${item.jumlah} × ${money(item.harga)}`));
                row.append(visual, copy, tag('strong', '', money(Number(item.harga) * Number(item.jumlah))));
                items.append(row);
                if (item.bisaUlas) items.append(formUlasan(item));
            });

            const bottom = tag('div', 'order-card-bottom');
            bottom.append(tag('span', '', `Total ${money(order.total)} · ${order.pembayaran}`));
            bottom.append(tag('span', '', `Penerima: ${order.nama} · ${order.alamat || ''}`));
            card.append(top, items, bottom);

            const bukti = order.buktiBayar;
            if (bukti) {
                const state = tag('span', 'order-proof-state', `Bukti bayar: ${bukti.status}`);
                const link = tag('a', 'table-footnote', ` ${bukti.namaFile}`); link.href = bukti.url; link.target = '_blank'; link.rel = 'noopener';
                state.append(link); bottom.append(state);
                if (bukti.status === 'Ditolak') card.append(tag('p', 'order-rejected-note', `Bukti ditolak admin: ${bukti.catatan || 'tidak sesuai'}. Silakan unggah ulang.`));
            }
            if (order.status === 'Menunggu pembayaran') card.append(kotakInstruksi(order), formUnggah(order, bukti?.status === 'Ditolak'));
            list.append(card);
        });
    }

    buttons.forEach(button => button.addEventListener('click', () => {
        filter = button.dataset.orderFilter;
        buttons.forEach(node => node.classList.toggle('is-active', node === button));
        render();
    }));
    muat();
});
