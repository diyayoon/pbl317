'use strict';

/* Dashboard customer: seluruh angka dan pesanan terbaru berasal dari /customer/api/dashboard-summary. */
document.addEventListener('DOMContentLoaded', async () => {
    const body = document.body;
    if (!body.dataset.userId || body.dataset.userRole !== 'customer') return;

    const make = (tag, className = '', text = undefined) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const money = value => `Rp${Number(value || 0).toLocaleString('id-ID')}`;
    const list = document.getElementById('customerRecentOrders');
    const set = (id, value) => { const node = document.getElementById(id); if (node) node.textContent = String(value); };

    const kosong = (teks) => {
        const empty = make('div', 'account-empty-state');
        const link = make('a', '', 'Jelajahi katalog →'); link.href = '/katalog';
        empty.append(make('p', '', teks), link);
        list.replaceChildren(empty);
    };

    try {
        const response = await fetch('/customer/api/dashboard-summary', { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        const data = await response.json().catch(() => ({}));
        if (response.status === 401) { window.location.href = data.login || '/auth/login'; return; }
        if (!response.ok) throw new Error(data.error || 'Ringkasan akun gagal dimuat.');
        const orders = Array.isArray(data.orders) ? data.orders : [];
        set('customerOrderCount', Number(data.order_count ?? orders.length));
        set('customerCartCount', (data.cart || []).reduce((sum, item) => sum + Number(item.jumlah || 1), 0));
        const addresses = Array.isArray(data.addresses) ? data.addresses : [];
        set('customerAddressCount', addresses.length);
        const completionNotice = document.getElementById('completeProfileNotice');
        if (completionNotice) completionNotice.hidden = addresses.length > 0;
        if (!list) return;
        if (!orders.length) { kosong('Belum ada pesanan pada akun ini.'); return; }
        list.replaceChildren();
        orders.forEach(order => {
            const card = make('article', 'customer-order-item');
            const emblem = make('div', 'customer-order-emblem', '♜'); emblem.setAttribute('aria-hidden', 'true');
            const info = make('div', 'customer-order-info');
            const names = (order.items || []).map(item => item.nama).filter(Boolean).join(', ');
            const date = new Date(order.date);
            const qty = (order.items || []).reduce((sum, item) => sum + Number(item.jumlah || 1), 0);
            info.append(
                make('span', 'customer-order-number', `PESANAN ${order.orderNumber || order.id}`),
                make('h3', '', names || 'Koleksi Albis Antique'),
                make('p', '', `${Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })} · ${qty} item`),
            );
            const total = make('div', 'customer-order-total');
            total.append(
                make('strong', '', money(order.total)),
                make('span', `customer-order-status ${order.status === 'Selesai' ? 'is-complete' : 'is-processing'}`, order.status),
            );
            card.append(emblem, info, total);
            list.append(card);
        });
    } catch (error) {
        if (list) kosong(error.message || 'Ringkasan akun gagal dimuat.');
    }
});
