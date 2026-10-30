'use strict';

/* Interaksi halaman admin: dashboard, transaksi, ulasan, kategori, dan pengguna. */
document.addEventListener('DOMContentLoaded', () => {
    const view = document.querySelector('[data-admin-view]')?.dataset.adminView || '';
    if (!view || view === 'products') return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
    const element = id => document.getElementById(id);
    const money = value => `Rp${Number(value || 0).toLocaleString('id-ID')}`;
    const make = (tag, className = '', text = undefined) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const put = (id, value) => { const node = element(id); if (node) node.textContent = String(value); };
    const STATUS = ['Menunggu pembayaran', 'Menunggu persetujuan', 'Diproses', 'Dikirim', 'Selesai', 'Dibatalkan'];
    const NEXT = {
        'Menunggu pembayaran': ['Dibatalkan'], 'Menunggu persetujuan': ['Dibatalkan'],
        'Diproses': ['Dikirim'], 'Dikirim': ['Selesai'], 'Selesai': [], 'Dibatalkan': [],
    };
    const statusTag = value => make(
        'span', `admin-status ${['Diproses', 'Dikirim', 'Selesai', 'Disetujui'].includes(value) ? 'is-paid' : 'is-pending'}`,
        value || 'Menunggu pembayaran',
    );

    async function api(url, options = {}) {
        const method = String(options.method || 'GET').toUpperCase();
        const headers = { Accept: 'application/json', ...(options.headers || {}) };
        if (options.body !== undefined && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
        if (!['GET', 'HEAD'].includes(method)) headers['X-CSRFToken'] = csrfToken;
        const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
        const payload = await response.json().catch(() => ({}));
        if (response.status === 401) { window.location.href = payload.login || '/auth/login'; throw new Error(payload.error || 'Sesi berakhir.'); }
        if (!response.ok) throw new Error(payload.error || `Permintaan gagal (${response.status}).`);
        return payload;
    }
    const kirim = (url, method, data) => api(url, { method, body: data === undefined ? undefined : JSON.stringify(data) });

    function toast(message, role = 'status') {
        let node = element('adminToast');
        if (!node) {
            node = make('div', 'albis-toast'); node.id = 'adminToast';
            node.setAttribute('aria-live', 'polite'); document.body.append(node);
        }
        node.setAttribute('role', role);
        node.textContent = message;
        node.classList.add('is-visible');
        window.clearTimeout(node._timer);
        node._timer = window.setTimeout(() => node.classList.remove('is-visible'), 3500);
    }

    const barisKosong = (body, kolom, teks) => {
        body.replaceChildren();
        const row = make('tr'); const cell = make('td', 'table-empty', teks); cell.colSpan = kolom; row.append(cell); body.append(row);
    };
    const tombol = (label, kelas, aksi) => {
        const b = make('button', kelas, label); b.type = 'button'; b.addEventListener('click', aksi); return b;
    };
    const waktu = iso => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }); };

    /* ---------------- DASHBOARD PENJUALAN ---------------- */
    async function dashboard() {
        const body = element('adminRecentOrders');
        if (!body) return;
        const [orders, report] = await Promise.all([
            api('/admin/api/pesanan'),
            api('/admin/api/laporan'),
        ]);

        put('adminRevenue', money(report.pendapatan));
        put('adminCompletedOrders', report.selesai || 0);
        put('adminItemsSold', report.produk_terjual || 0);
        put('adminUserCount', report.pelanggan_aktif || 0);
        put('adminSalesPeriodTotal', money((report.bulanan || []).reduce((sum, item) => sum + Number(item.pendapatan || 0), 0)));

        const chart = element('adminSalesChart');
        if (chart) {
            chart.replaceChildren();
            const months = report.bulanan || [];
            const highest = Math.max(1, ...months.map(item => Number(item.pendapatan || 0)));
            if (!months.length) {
                chart.append(make('p', 'table-empty', 'Belum ada data penjualan.'));
            } else {
                months.forEach(item => {
                    const column = make('div', 'admin-sales-month');
                    const value = make('strong', 'admin-sales-month-value', money(item.pendapatan));
                    const track = make('div', 'admin-sales-bar-track');
                    const bar = make('span', 'admin-sales-bar');
                    const revenue = Number(item.pendapatan || 0);
                    bar.style.height = `${revenue ? Math.max(4, (revenue / highest) * 100) : 0}%`;
                    bar.title = `${item.bulan}: ${money(revenue)} (${item.pesanan || 0} pesanan selesai)`;
                    track.append(bar);
                    const label = make('span', 'admin-sales-month-label', item.bulan);
                    column.append(value, track, label);
                    chart.append(column);
                });
            }
        }

        const top = element('adminTopProducts');
        if (top) {
            top.replaceChildren();
            const products = report.terlaris || [];
            if (!products.length) top.append(make('p', 'table-empty', 'Belum ada produk terjual.'));
            products.forEach((product, index) => {
                const row = make('div', 'admin-top-product-row');
                row.append(
                    make('span', 'admin-top-product-rank', String(index + 1)),
                    make('strong', 'admin-top-product-name', product.nama),
                    make('span', 'admin-top-product-count', `${product.terjual} terjual`),
                );
                top.append(row);
            });
        }

        const statuses = element('adminSalesStatuses');
        if (statuses) {
            statuses.replaceChildren();
            const statusItems = [
                ['Menunggu pembayaran', report.menunggu_pembayaran],
                ['Menunggu persetujuan', report.menunggu_persetujuan],
                ['Diproses', report.diproses],
                ['Dikirim', report.dikirim],
                ['Selesai', report.selesai],
                ['Dibatalkan', report.dibatalkan],
            ];
            statusItems.forEach(([label, value]) => {
                const item = make('div', 'admin-sales-status-item');
                item.append(make('span', '', label), make('strong', '', String(value || 0)));
                statuses.append(item);
            });
        }

        if (!orders.length) {
            barisKosong(body, 4, 'Belum ada pesanan.');
            return;
        }
        body.replaceChildren();
        orders.slice(0, 5).forEach(order => {
            const row = make('tr');
            row.append(make('td', '', `#${order.orderNumber}`), make('td', '', order.nama), make('td', '', money(order.total)));
            const status = make('td');
            status.append(statusTag(order.status));
            row.append(status);
            body.append(row);
        });
    }

    /* ---------------- PESANAN ---------------- */
    let orders = [];
    function renderOrders() {
        const body = element('adminOrdersBody'); if (!body) return;
        const term = String(element('adminOrderSearch')?.value || '').trim().toLocaleLowerCase('id-ID');
        const rows = orders.filter(o => `${o.orderNumber} ${o.nama} ${o.status}`.toLocaleLowerCase('id-ID').includes(term));
        if (!rows.length) { barisKosong(body, 6, 'Belum ada pesanan yang cocok.'); return; }
        body.replaceChildren();
        rows.forEach(order => {
            const row = make('tr');
            const names = (order.items || []).map(i => `${i.nama} × ${i.jumlah}`).join(', ') || '—';
            row.append(make('td', '', `#${order.orderNumber}`), make('td', '', order.nama), make('td', '', names), make('td', '', money(order.total)));
            const st = make('td'); st.append(statusTag(order.status)); row.append(st);
            const act = make('td');
            const opsi = NEXT[order.status] || [];
            if (!opsi.length) act.append(make('span', 'table-footnote', 'Selesai'));
            else {
                const select = make('select', 'form-control');
                select.setAttribute('aria-label', `Status pesanan ${order.orderNumber}`);
                [order.status, ...opsi].forEach(s => { const o = make('option', '', s); o.value = s; select.append(o); });
                select.addEventListener('change', async () => {
                    if (select.value === order.status) return;
                    if (select.value === 'Dibatalkan' && !window.confirm(`Batalkan pesanan #${order.orderNumber}? Stok akan dikembalikan.`)) { select.value = order.status; return; }
                    select.disabled = true;
                    try { await kirim(`/admin/api/pesanan/${order.id}`, 'PATCH', { status: select.value }); toast('Status pesanan diperbarui.'); await muatOrders(); }
                    catch (error) { select.value = order.status; toast(error.message, 'alert'); }
                    finally { select.disabled = false; }
                });
                act.append(select);
            }
            row.append(act); body.append(row);
        });
    }
    async function muatOrders() { orders = await api('/admin/api/pesanan'); renderOrders(); }

    /* ---------------- PEMBAYARAN ---------------- */
    async function pembayaran() {
        const body = element('adminPaymentsBody'); if (!body) return;
        const payments = await api('/admin/api/pembayaran');
        if (!payments.length) { barisKosong(body, 7, 'Belum ada pembayaran yang tercatat.'); return; }
        body.replaceChildren();
        payments.forEach(p => {
            const row = make('tr');
            row.append(make('td', '', `#${p.order_number}`), make('td', '', p.customer));
            row.append(make('td', '', p.gateway_payment_type || p.method || 'Midtrans'), make('td', '', money(p.total)));
            const st = make('td'); st.append(statusTag(p.status)); row.append(st);
            const detailStatus = p.gateway_status
                ? `Status gerbang pembayaran: ${p.gateway_status}`
                : (p.catatan || (p.method === 'Midtrans' ? 'Diperbarui otomatis oleh Midtrans.' : 'Tidak ada catatan.'));
            row.append(make('td', '', detailStatus));

            const act = make('td', 'table-actions');
            if (p.bukti_url && p.status === 'Menunggu persetujuan') {
                const proof = make('a', 'button button-secondary button-small', 'Lihat bukti');
                proof.href = p.bukti_url; proof.target = '_blank'; proof.rel = 'noopener noreferrer';
                act.append(proof,
                    tombol('Setujui', 'button button-primary button-small', () => tinjau(p, 'approve', '')),
                    tombol('Tolak', 'button button-secondary button-small', () => {
                        const note = (window.prompt('Alasan penolakan bukti pembayaran:') || '').trim();
                        if (note.length < 3) { toast('Alasan penolakan minimal 3 karakter.', 'alert'); return; }
                        tinjau(p, 'reject', note);
                    }),
                );
            } else if (p.status === 'Disetujui') {
                act.textContent = p.method === 'Midtrans' ? 'Terkonfirmasi otomatis' : 'Bukti telah disetujui';
            } else if (p.status === 'Menunggu pembayaran') {
                act.textContent = 'Menunggu pembayaran pelanggan';
            } else {
                act.textContent = p.status === 'Ditolak' ? 'Menunggu bukti pembayaran ulang' : 'Tidak ada tindakan';
            }
            row.append(act); body.append(row);
        });
    }
    async function tinjau(p, aksi, catatan) {
        try {
            await kirim(`/admin/api/pembayaran/${p.id}/tinjau`, 'POST', { aksi, catatan });
            toast(aksi === 'approve' ? 'Bukti pembayaran disetujui.' : 'Bukti pembayaran ditolak.');
            await Promise.all([pembayaran(), muatOrders()]);
        } catch (error) { toast(error.message, 'alert'); }
    }

    /* ---------------- PESANAN & PEMBAYARAN ---------------- */
    async function transaksi() {
        const tabs = [...document.querySelectorAll('[data-admin-tab]')];
        const panels = [...document.querySelectorAll('[data-admin-panel]')];
        const aktifkanTab = (key, updateHash = true) => {
            tabs.forEach(tab => {
                const active = tab.dataset.adminTab === key;
                tab.classList.toggle('is-active', active);
                tab.setAttribute('aria-selected', String(active));
                tab.tabIndex = active ? 0 : -1;
            });
            panels.forEach(panel => { panel.hidden = panel.dataset.adminPanel !== key; });
            if (updateHash) history.replaceState(null, '', `${location.pathname}${location.search}#${key}`);
        };

        tabs.forEach((tab, index) => {
            tab.addEventListener('click', () => aktifkanTab(tab.dataset.adminTab));
            tab.addEventListener('keydown', event => {
                let tujuan = null;
                if (event.key === 'ArrowRight') tujuan = tabs[(index + 1) % tabs.length];
                if (event.key === 'ArrowLeft') tujuan = tabs[(index - 1 + tabs.length) % tabs.length];
                if (event.key === 'Home') tujuan = tabs[0];
                if (event.key === 'End') tujuan = tabs[tabs.length - 1];
                if (tujuan) {
                    event.preventDefault();
                    aktifkanTab(tujuan.dataset.adminTab);
                    tujuan.focus();
                }
            });
        });
        const tabAwal = location.hash === '#pembayaran' ? 'pembayaran' : 'pesanan';
        aktifkanTab(tabAwal, false);
        await Promise.all([muatOrders(), pembayaran()]);
    }

    /* ---------------- ULASAN ---------------- */
    async function ulasan() {
        const body = element('adminReviewsBody'); if (!body) return;
        const data = await api('/admin/api/ulasan');
        if (!data.length) { barisKosong(body, 6, 'Belum ada ulasan.'); return; }
        body.replaceChildren();
        data.forEach(r => {
            const row = make('tr');
            row.append(make('td', '', r.produk), make('td', '', r.nama), make('td', '', '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating)), make('td', '', r.komentar || '—'));
            const st = make('td'); st.append(make('span', `admin-status ${r.tersembunyi ? 'is-pending' : 'is-paid'}`, r.tersembunyi ? 'Disembunyikan' : 'Tampil'));
            if (r.tersembunyi && r.alasan) st.append(make('small', 'table-footnote', ` — ${r.alasan}`));
            row.append(st);
            const act = make('td');
            if (r.tersembunyi) act.append(tombol('Tampilkan', 'button button-secondary button-small', () => moderasi(r, false, '')));
            else act.append(tombol('Sembunyikan', 'button button-secondary button-small', () => {
                const alasan = (window.prompt('Alasan menyembunyikan ulasan (wajib, dicatat di audit):') || '').trim();
                if (alasan.length < 3) { toast('Alasan wajib diisi.', 'alert'); return; }
                moderasi(r, true, alasan);
            }));
            row.append(act); body.append(row);
        });
    }
    async function moderasi(r, sembunyikan, alasan) {
        try { await kirim(`/admin/api/ulasan/${r.id}/moderasi`, 'POST', { sembunyikan, alasan }); toast('Moderasi tersimpan.'); await ulasan(); }
        catch (error) { toast(error.message, 'alert'); }
    }

    /* ---------------- KATEGORI ---------------- */
    let editId = null;
    let categoryPreviewUrl = '';
    let kategoriAkanDihapus = null;
    const categoryForm = element('categoryForm');
    const categoryImage = element('categoryImageInput');
    const categoryPreview = element('categoryImagePreview');
    const categoryDialog = element('categoryDeleteDialog');
    const categoryDialogTitle = element('categoryDeleteTitle');
    const categoryDialogMessage = element('categoryDeleteMessage');
    const categoryDialogConfirm = element('categoryDeleteConfirm');

    function clearCategoryPreviewUrl() {
        if (categoryPreviewUrl) URL.revokeObjectURL(categoryPreviewUrl);
        categoryPreviewUrl = '';
    }

    function showCategoryPreview(source) {
        if (!categoryPreview) return;
        categoryPreview.src = source || '';
        categoryPreview.hidden = !source;
    }

    categoryImage?.addEventListener('change', () => {
        const file = categoryImage.files?.[0];
        if (!file) return;
        const extension = file.name.split('.').pop()?.toLowerCase();
        const accepted = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type)
            || (!file.type && ['jpg', 'jpeg', 'png', 'webp'].includes(extension));
        if (!accepted || file.size > 3 * 1024 * 1024) {
            categoryImage.value = '';
            showCategoryPreview(categoryPreview?.dataset.originalSrc || '');
            toast('Pilih foto JPG, PNG, atau WEBP maksimal 3 MB.', 'alert');
            return;
        }
        clearCategoryPreviewUrl();
        categoryPreviewUrl = URL.createObjectURL(file);
        showCategoryPreview(categoryPreviewUrl);
    });

    async function kategori() {
        const body = element('adminCategoriesBody');
        if (!body) return;
        const data = await api('/admin/api/kategori');
        if (!data.length) { barisKosong(body, 5, 'Belum ada kategori.'); return; }
        body.replaceChildren();
        data.forEach(k => {
            const row = make('tr');
            const photoCell = make('td');
            if (k.gambar) {
                const img = make('img', 'category-admin-table-photo');
                img.src = k.gambar;
                img.alt = `Foto kategori ${k.nama}`;
                img.loading = 'lazy';
                photoCell.append(img);
            } else photoCell.textContent = 'Belum ada foto';
            row.append(photoCell, make('td', '', k.nama), make('td', '', String(k.jumlah_produk)));
            const status = make('td');
            status.append(make('span', `admin-status ${k.aktif ? 'is-paid' : 'is-pending'}`, k.aktif ? 'Aktif' : 'Nonaktif'));
            row.append(status);
            const actions = make('td', 'table-actions');
            actions.append(
                tombol('Ubah', 'button button-secondary button-small', () => {
                    editId = k.id;
                    element('categoryName').value = k.nama;
                    if (categoryImage) { categoryImage.value = ''; categoryImage.required = false; }
                    clearCategoryPreviewUrl();
                    if (categoryPreview) categoryPreview.dataset.originalSrc = k.gambar || '';
                    showCategoryPreview(k.gambar || '');
                    element('categorySubmit').textContent = 'Simpan perubahan';
                    categoryForm?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    element('categoryName').focus({ preventScroll: true });
                }),
                tombol('Hapus', 'button button-secondary button-small', () => bukaDialogHapusKategori(k)),
            );
            row.append(actions);
            body.append(row);
        });
    }

    function bukaDialogHapusKategori(kategori) {
        if (!categoryDialog) return;
        kategoriAkanDihapus = kategori;
        const dipakai = Number(kategori.jumlah_produk || 0) > 0;
        categoryDialogTitle.textContent = dipakai ? 'Nonaktifkan kategori?' : 'Hapus kategori?';
        categoryDialogMessage.textContent = dipakai
            ? `Kategori ${kategori.nama} masih digunakan ${kategori.jumlah_produk} produk. Kategori akan dinonaktifkan; produk dan riwayat pesanan tetap tersimpan.`
            : `Kategori ${kategori.nama} akan dihapus dari katalog.`;
        categoryDialogConfirm.textContent = dipakai ? 'Nonaktifkan kategori' : 'Hapus kategori';
        categoryDialog.hidden = false;
        document.body.classList.add('admin-dialog-open');
        categoryDialogConfirm.focus();
    }

    function tutupDialogHapusKategori() {
        if (!categoryDialog) return;
        categoryDialog.hidden = true;
        document.body.classList.remove('admin-dialog-open');
        kategoriAkanDihapus = null;
    }

    element('categoryDeleteCancel')?.addEventListener('click', tutupDialogHapusKategori);
    categoryDialog?.addEventListener('click', event => {
        if (event.target === categoryDialog) tutupDialogHapusKategori();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && categoryDialog && !categoryDialog.hidden) tutupDialogHapusKategori();
    });
    categoryDialogConfirm?.addEventListener('click', async () => {
        if (!kategoriAkanDihapus) return;
        const kategori = kategoriAkanDihapus;
        categoryDialogConfirm.disabled = true;
        try {
            const result = await kirim(`/admin/api/kategori/${kategori.id}`, 'DELETE');
            tutupDialogHapusKategori();
            toast(result.message || 'Kategori diperbarui.');
            if (editId === kategori.id) resetFormKategori();
            await kategori();
        } catch (error) {
            toast(error.message, 'alert');
        } finally {
            categoryDialogConfirm.disabled = false;
        }
    });

    function resetFormKategori() {
        editId = null;
        categoryForm?.reset();
        if (categoryImage) categoryImage.required = true;
        clearCategoryPreviewUrl();
        showCategoryPreview('');
        if (categoryPreview) delete categoryPreview.dataset.originalSrc;
        if (element('categorySubmit')) element('categorySubmit').textContent = 'Tambah kategori';
    }

    categoryForm?.addEventListener('submit', async event => {
        event.preventDefault();
        const nama = element('categoryName').value.trim();
        const file = categoryImage?.files?.[0];
        if (!nama) { toast('Nama kategori wajib diisi.', 'alert'); element('categoryName').focus(); return; }
        if (!editId && !file) { toast('Foto kategori wajib dipilih.', 'alert'); categoryImage?.focus(); return; }
        const data = new FormData();
        data.append('nama', nama);
        data.append('aktif', 'true');
        if (file) data.append('gambar', file);
        const url = editId ? `/admin/api/kategori/${editId}` : '/admin/api/kategori';
        const submit = element('categorySubmit');
        submit.disabled = true;
        try {
            const response = await fetch(url, {
                method: editId ? 'PUT' : 'POST', credentials: 'same-origin',
                headers: { Accept: 'application/json', 'X-CSRFToken': csrfToken }, body: data,
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result.error || `Permintaan gagal (${response.status}).`);
            toast(result.message || 'Kategori tersimpan.');
            resetFormKategori();
            await kategori();
        } catch (error) {
            toast(error.message, 'alert');
        } finally {
            submit.disabled = false;
        }
    });

    /* ---------------- PENGGUNA ---------------- */
    async function pengguna() {
        const body = element('userRows');
        const box = element('userDetail');
        if (!body) return;
        const q = element('userSearch')?.value.trim() || '';
        const status = element('userStatusFilter')?.value || '';
        const list = await api(`/admin/api/pengguna?q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}`);
        put('userCount', `${list.length} pengguna`);
        if (!list.length) {
            barisKosong(body, 7, 'Tidak ada pengguna yang cocok.');
            if (box) box.hidden = true;
            return;
        }
        body.replaceChildren();

        const aksi = async (path, method, data, pesan) => {
            try {
                await kirim(path, method, data);
                toast(pesan);
                if (box) box.hidden = true;
                await pengguna();
            } catch (error) {
                toast(error.message, 'alert');
            }
        };

        list.forEach(u => {
            const row = make('tr');
            const nameCell = make('td');
            nameCell.append(make('strong', '', u.nama));
            const emailCell = make('td', 'admin-user-email', u.email);
            const statusCell = make('td');
            statusCell.append(make('span', `admin-status ${u.status === 'Aktif' ? 'is-paid' : 'is-pending'}`, u.status));
            statusCell.append(make('small', 'admin-user-verification', u.terverifikasi ? 'Terverifikasi' : 'Belum verifikasi'));
            row.append(nameCell, emailCell, make('td', '', u.telepon || '—'), make('td', '', String(u.jumlahPesanan)),
                make('td', '', waktu(u.bergabung)), statusCell);

            const actionCell = make('td', 'admin-user-actions-cell');
            const menu = make('div', 'admin-user-actions');
            const trigger = tombol('⋯', 'admin-user-actions-trigger', () => {
                const open = !menu.classList.contains('is-open');
                document.querySelectorAll('.admin-user-actions.is-open').forEach(item => {
                    item.classList.remove('is-open');
                    item.querySelector('.admin-user-actions-trigger')?.setAttribute('aria-expanded', 'false');
                });
                menu.classList.toggle('is-open', open);
                trigger.setAttribute('aria-expanded', String(open));
            });
            trigger.setAttribute('aria-label', `Aksi untuk ${u.nama}`);
            trigger.setAttribute('aria-expanded', 'false');
            const listMenu = make('div', 'admin-user-actions-menu');
            const pilih = (label, callback, danger = false) => {
                const button = tombol(label, `admin-user-action-item${danger ? ' is-danger' : ''}`, () => {
                    menu.classList.remove('is-open');
                    trigger.setAttribute('aria-expanded', 'false');
                    callback();
                });
                listMenu.append(button);
            };

            pilih('Lihat detail', async () => {
                try { renderDetail(box, await api(`/admin/api/pengguna/${u.id}`)); }
                catch (error) { toast(error.message, 'alert'); }
            });

            if (u.status === 'Aktif') {
                pilih('Nonaktifkan', () => {
                    const alasan = (window.prompt(`Alasan menonaktifkan ${u.email}:`) || '').trim();
                    if (alasan.length < 5) { toast('Alasan minimal 5 karakter.', 'alert'); return; }
                    aksi(`/admin/api/pengguna/${u.id}/status`, 'POST', { aksi: 'nonaktifkan', alasan }, 'Akun dinonaktifkan.');
                });
            } else if (u.status === 'Nonaktif') {
                pilih('Aktifkan', () => aksi(`/admin/api/pengguna/${u.id}/status`, 'POST', { aksi: 'aktifkan' }, 'Akun diaktifkan.'));
            }

            if (u.status !== 'Dihapus') {
                pilih('Hapus pengguna', () => {
                    const konfirmasi = (window.prompt(`Ketik email ${u.email} untuk mengonfirmasi penghapusan akun.`) || '').trim();
                    if (!konfirmasi) return;
                    aksi(`/admin/api/pengguna/${u.id}`, 'DELETE', { konfirmasi_email: konfirmasi, alasan: 'dihapus oleh admin' }, 'Akun dihapus.');
                }, true);
            }

            menu.append(trigger, listMenu);
            actionCell.append(menu);
            row.append(actionCell);
            body.append(row);
        });
    }

    function renderDetail(box, d) {
        box.replaceChildren(); box.hidden = false;
        box.append(make('h3', '', `Detail: ${d.nama}`));
        [['Email', d.email], ['Verifikasi email', d.terverifikasi ? 'Sudah' : 'Belum'], ['Status', d.status + (d.alasan ? ` (${d.alasan})` : '')], ['Pesanan', d.jumlahPesanan],
            ['Ulasan', d.jumlahUlasan], ['Alamat tersimpan', d.jumlahAlamat]].forEach(([k, v]) => {
            const r = make('div', 'admin-report-status-row'); r.append(make('span', '', k), make('strong', '', String(v))); box.append(r);
        });
        box.append(make('h4', '', 'Aktivitas terakhir'));
        if (!d.aktivitas.length) box.append(make('p', '', 'Belum ada aktivitas tercatat.'));
        d.aktivitas.forEach(a => {
            const r = make('div', 'admin-report-status-row');
            r.append(make('span', '', `${waktu(a.waktu)} · ${a.aksi} · ${a.aktor}`), make('strong', '', a.detail || ''));
            box.append(r);
        });
    }
    const jadwalkanPencarianPengguna = () => { window.clearTimeout(window._userT); window._userT = window.setTimeout(() => pengguna().catch(error => toast(error.message, 'alert')), 250); };
    element('userSearch')?.addEventListener('input', jadwalkanPencarianPengguna);
    element('userStatusFilter')?.addEventListener('change', () => pengguna().catch(error => toast(error.message, 'alert')));
    document.addEventListener('click', event => {
        if (event.target.closest('.admin-user-actions')) return;
        document.querySelectorAll('.admin-user-actions.is-open').forEach(menu => {
            menu.classList.remove('is-open');
            menu.querySelector('.admin-user-actions-trigger')?.setAttribute('aria-expanded', 'false');
        });
    });

    element('adminOrderSearch')?.addEventListener('input', renderOrders);
    const jalan = { dashboard, orders: muatOrders, payments: pembayaran, 'orders-payments': transaksi, reviews: ulasan, categories: kategori, users: pengguna }[view];
    if (jalan) jalan().catch(error => toast(`Data tidak dapat dimuat: ${error.message}`, 'alert'));
});
