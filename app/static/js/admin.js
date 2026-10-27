'use strict';

/* Panel admin: pesanan, pembayaran, laporan, ulasan, kategori, dan pengguna. Semua data dari API PostgreSQL. */
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

    /* ---------------- DASHBOARD ---------------- */
    async function dashboard() {
        const body = element('adminRecentOrders'); if (!body) return;
        const orders = await api('/admin/api/pesanan');
        if (!orders.length) { barisKosong(body, 4, 'Belum ada pesanan.'); return; }
        body.replaceChildren();
        orders.slice(0, 5).forEach(order => {
            const row = make('tr');
            row.append(make('td', '', `#${order.orderNumber}`), make('td', '', order.nama), make('td', '', money(order.total)));
            const st = make('td'); st.append(statusTag(order.status)); row.append(st);
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
            if (!opsi.length) act.append(make('span', 'table-footnote', 'Final'));
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
        if (!payments.length) { barisKosong(body, 6, 'Belum ada pembayaran yang tercatat.'); return; }
        body.replaceChildren();
        payments.forEach(p => {
            const row = make('tr');
            row.append(make('td', '', `#${p.order_number}`), make('td', '', p.customer));
            row.append(make('td', '', p.gateway_payment_type || p.method || 'Midtrans'), make('td', '', money(p.total)));
            const st = make('td'); st.append(statusTag(p.status));
            const detailStatus = p.gateway_status ? `Status gateway: ${p.gateway_status}` : (p.catatan || 'Status diperbarui otomatis oleh Midtrans.');
            st.append(make('small', 'table-footnote', ` — ${detailStatus}`)); row.append(st);
            const act = make('td', '', p.status === 'Disetujui' ? 'Terkonfirmasi otomatis' : (p.status === 'Menunggu pembayaran' ? 'Menunggu pembayaran pelanggan' : 'Tidak ada tindakan'));
            row.append(act); body.append(row);
        });
    }
    async function tinjau(p, aksi, catatan) {
        try { await kirim(`/admin/api/pembayaran/${p.id}/tinjau`, 'POST', { aksi, catatan }); toast('Keputusan pembayaran disimpan.'); await pembayaran(); }
        catch (error) { toast(error.message, 'alert'); }
    }

    /* ---------------- LAPORAN ---------------- */
    async function laporan() {
        const r = await api('/admin/api/laporan');
        put('reportOrderCount', r.pesanan); put('reportPendingCount', r.menunggu_pembayaran);
        put('reportCompletedCount', r.selesai); put('reportCompletedValue', money(r.pendapatan));
        const summary = element('reportStatusSummary');
        if (summary) {
            summary.replaceChildren();
            if (!r.pesanan) summary.append(make('p', 'table-footnote', 'Belum ada transaksi.'));
            STATUS.forEach(s => { const row = make('div', 'admin-report-status-row'); row.append(make('span', '', s), make('strong', '', String((r.status || {})[s] || 0))); summary.append(row); });
        }
        const top = element('reportTopProducts');
        if (top) {
            top.replaceChildren();
            if (!(r.terlaris || []).length) top.append(make('p', 'table-footnote', 'Belum ada penjualan yang dibayar.'));
            (r.terlaris || []).forEach(t => { const row = make('div', 'admin-report-status-row'); row.append(make('span', '', t.nama), make('strong', '', `${t.terjual} terjual`)); top.append(row); });
        }
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
    const categoryForm = element('categoryForm');
    const categoryImage = element('categoryImageInput');
    const categoryPreview = element('categoryImagePreview');
    categoryImage?.addEventListener('change', () => {
        const file = categoryImage.files?.[0];
        if (!file) return;
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 3 * 1024 * 1024) {
            categoryImage.value = '';
            toast('Pilih foto JPG, PNG, atau WEBP maksimal 3 MB.', 'alert');
            return;
        }
        if (categoryPreview) { categoryPreview.src = URL.createObjectURL(file); categoryPreview.hidden = false; }
    });
    async function kategori() {
        const body = element('adminCategoriesBody'); if (!body) return;
        const data = await api('/admin/api/kategori');
        if (!data.length) { barisKosong(body, 5, 'Belum ada kategori.'); return; }
        body.replaceChildren();
        data.forEach(k => {
            const row = make('tr');
            const photoCell = make('td');
            if (k.gambar) {
                const img = make('img', 'category-admin-table-photo'); img.src = k.gambar; img.alt = `Foto kategori ${k.nama}`; img.loading = 'lazy'; photoCell.append(img);
            } else photoCell.textContent = 'Belum ada foto';
            row.append(photoCell, make('td', '', k.nama), make('td', '', String(k.jumlah_produk)));
            const st = make('td'); st.append(make('span', `admin-status ${k.aktif ? 'is-paid' : 'is-pending'}`, k.aktif ? 'Aktif' : 'Nonaktif')); row.append(st);
            const act = make('td', 'table-actions');
            act.append(
                tombol('Ubah', 'button button-secondary button-small', () => {
                    editId = k.id; element('categoryName').value = k.nama;
                    if (categoryImage) { categoryImage.value = ''; categoryImage.required = false; }
                    if (categoryPreview) { categoryPreview.src = k.gambar || ''; categoryPreview.hidden = !k.gambar; }
                    element('categorySubmit').textContent = 'Simpan perubahan'; element('categoryName').focus();
                    categoryForm?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }),
                tombol('Hapus', 'button button-secondary button-small', async () => {
                    const pesan = k.jumlah_produk > 0
                        ? `Kategori "${k.nama}" masih dipakai ${k.jumlah_produk} produk. Kategori akan dinonaktifkan agar produk dan riwayat tetap utuh. Lanjutkan?`
                        : `Hapus kategori "${k.nama}"?`;
                    if (!window.confirm(pesan)) return;
                    try { const res = await kirim(`/admin/api/kategori/${k.id}`, 'DELETE'); toast(res.message); if (editId === k.id) resetFormKategori(); await kategori(); }
                    catch (error) { toast(error.message, 'alert'); }
                }),
            );
            row.append(act); body.append(row);
        });
    }
    function resetFormKategori() {
        editId = null; categoryForm?.reset();
        if (categoryImage) categoryImage.required = true;
        if (categoryPreview) { categoryPreview.removeAttribute('src'); categoryPreview.hidden = true; }
        if (element('categorySubmit')) element('categorySubmit').textContent = 'Tambah kategori';
    }
    categoryForm?.addEventListener('submit', async event => {
        event.preventDefault();
        const nama = element('categoryName').value.trim();
        const file = categoryImage?.files?.[0];
        if (!editId && !file) { toast('Foto kategori wajib dipilih.', 'alert'); categoryImage?.focus(); return; }
        const data = new FormData(); data.append('nama', nama); data.append('aktif', 'true');
        if (file) data.append('gambar', file);
        const url = editId ? `/admin/api/kategori/${editId}` : '/admin/api/kategori';
        try {
            const response = await fetch(url, { method: editId ? 'PUT' : 'POST', credentials: 'same-origin', headers: { Accept: 'application/json', 'X-CSRFToken': csrfToken }, body: data });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result.error || `Permintaan gagal (${response.status}).`);
            toast(result.message || 'Kategori tersimpan.'); resetFormKategori(); await kategori();
        } catch (error) { toast(error.message, 'alert'); }
    });

    /* ---------------- PENGGUNA ---------------- */
    async function pengguna() {
        const body = element('userRows'); const box = element('userDetail');
        const q = element('userSearch')?.value.trim() || '';
        const list = await api(`/admin/api/pengguna?q=${encodeURIComponent(q)}`);
        put('userCount', `${list.length} customer ditemukan.`);
        if (!list.length) { barisKosong(body, 7, 'Tidak ada customer.'); return; }
        body.replaceChildren();
        const aksi = async (path, method, data, ok) => {
            try { await kirim(path, method, data); toast(ok); box.hidden = true; await pengguna(); }
            catch (error) { toast(error.message, 'alert'); }
        };
        list.forEach(u => {
            const row = make('tr');
            const nama = make('td'); nama.append(make('strong', '', u.nama));
            const st = make('td'); st.append(statusTag(u.status === 'Aktif' ? 'Selesai' : u.status)); st.append(make('div', 'table-footnote', u.terverifikasi ? 'Email terverifikasi' : 'Email belum terverifikasi'));
            row.append(nama, make('td', '', u.email), make('td', '', u.telepon || '—'), make('td', '', String(u.jumlahPesanan)),
                make('td', '', waktu(u.bergabung)), st);
            const act = make('td', 'table-actions');
            act.append(tombol('Detail', 'btn btn-secondary btn-small', async () => {
                try { renderDetail(box, await api(`/admin/api/pengguna/${u.id}`)); } catch (error) { toast(error.message, 'alert'); }
            }));
            if (u.status === 'Aktif') {
                act.append(tombol('Nonaktifkan', 'btn btn-secondary btn-small', () => {
                    const alasan = window.prompt(`Alasan menonaktifkan ${u.email}:`); if (alasan === null) return;
                    aksi(`/admin/api/pengguna/${u.id}/status`, 'POST', { aksi: 'nonaktifkan', alasan }, 'Akun dinonaktifkan.');
                }));
                act.append(tombol('Blokir', 'btn btn-secondary btn-small', () => {
                    const alasan = window.prompt(`Alasan memblokir ${u.email}:`); if (alasan === null) return;
                    aksi(`/admin/api/pengguna/${u.id}/status`, 'POST', { aksi: 'blokir', alasan }, 'Akun diblokir.');
                }));
            } else if (u.status === 'Nonaktif') {
                act.append(tombol('Aktifkan', 'btn btn-primary btn-small', () =>
                    aksi(`/admin/api/pengguna/${u.id}/status`, 'POST', { aksi: 'aktifkan' }, 'Akun diaktifkan kembali.')));
            }
            if (u.status !== 'Dihapus') {
                act.append(tombol('Hapus', 'btn btn-secondary btn-small', () => {
                    const konfirmasi = window.prompt(`Hapus akun (data pribadi dianonimkan, riwayat pesanan tetap). Ketik email ${u.email} untuk konfirmasi:`);
                    if (konfirmasi === null) return;
                    aksi(`/admin/api/pengguna/${u.id}`, 'DELETE', { konfirmasi_email: konfirmasi, alasan: 'dihapus oleh admin' }, 'Akun dihapus.');
                }));
            }
            row.append(act); body.append(row);
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
    element('userSearch')?.addEventListener('input', () => { window.clearTimeout(window._userT); window._userT = window.setTimeout(() => pengguna().catch(() => {}), 250); });

    element('adminOrderSearch')?.addEventListener('input', renderOrders);
    const jalan = { dashboard, orders: muatOrders, payments: pembayaran, reports: laporan, reviews: ulasan, categories: kategori, users: pengguna }[view];
    if (jalan) jalan().catch(error => toast(`Data tidak dapat dimuat: ${error.message}`, 'alert'));
});
