'use strict';

/* Checkout: data keranjang/alamat dari /customer/api/checkout; pesanan dibuat lewat /customer/api/orders.
   Harga, stok, dan total selalu dihitung ulang oleh server. */
(() => {
    const money = value => `Rp${Number(value || 0).toLocaleString('id-ID')}`;
    async function mulaiCheckout() {
        const form = document.getElementById('checkoutForm');
        const empty = document.getElementById('checkoutEmpty');
        const success = document.getElementById('checkoutSuccess');
        const itemsNode = document.getElementById('checkoutItems');
        const totalNode = document.getElementById('checkoutTotal');
        const subtotalNode = document.getElementById('checkoutSubtotal');
        const addressList = document.getElementById('checkoutAddresses');
        const addressFeedback = document.getElementById('checkoutAddressFeedback');
        const submit = document.getElementById('checkoutSubmit');
        const url = new URL(window.location.href);
        const directId = Number(url.searchParams.get('direct_product_id') || 0) || null;
        const directQuantity = Math.max(1, Number(url.searchParams.get('quantity') || 1));
        const money = value => `Rp${Number(value || 0).toLocaleString('id-ID')}`;
        const make = (tag, cls = '', value = undefined) => {
            const node = document.createElement(tag);
            if (cls) node.className = cls;
            if (value !== undefined) node.textContent = value;
            return node;
        };
        const request = async (path, method = 'GET', payload = undefined) => {
            const headers = { Accept: 'application/json' };
            const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
            if (csrf) headers['X-CSRFToken'] = csrf;
            const options = { method, credentials: 'same-origin', headers };
            if (payload !== undefined) { headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(payload); }
            const response = await fetch(path, options);
            const body = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(body.error || `Permintaan gagal (${response.status}).`);
            return body;
        };
        const showError = message => {
            addressFeedback.textContent = message;
            addressFeedback.hidden = false;
        };
        let selectedAddressId = null;
        let checkoutItems = [];

        try {
            const query = directId ? `?direct_product_id=${encodeURIComponent(directId)}&quantity=${encodeURIComponent(directQuantity)}` : '';
            const data = await request(`/customer/api/checkout${query}`);
            checkoutItems = Array.isArray(data.items) ? data.items : [];
            const addresses = Array.isArray(data.addresses?.daftar) ? data.addresses.daftar : [];
            selectedAddressId = data.addresses?.utamaId || addresses[0]?.id || null;
            addressList.replaceChildren();
            if (!addresses.length) {
                showError('Belum ada alamat lengkap di profil. Tambahkan alamat sebelum checkout.');
            } else {
                addresses.forEach((address, index) => {
                    const complete = Boolean(address.penerima && address.telepon && address.kodePos && address.provinsi && address.kota && address.kecamatan && address.lengkap && address.lengkap.trim().length >= 10);
                    const option = make('div', 'checkout-address-option' + (complete ? '' : ' is-incomplete'));
                    const label = make('label', 'checkout-address-option-label');
                    const radio = document.createElement('input');
                    radio.type = 'radio'; radio.name = 'alamatId'; radio.value = address.id;
                    radio.checked = String(address.id) === String(selectedAddressId) && complete;
                    radio.disabled = !complete; radio.id = `checkoutAddress_${index}`;
                    const copy = make('span', 'checkout-address-copy');
                    const title = make('span', 'checkout-address-label-line');
                    title.append(make('strong', '', address.label || 'Alamat tersimpan'));
                    if (String(address.id) === String(data.addresses?.utamaId)) title.append(make('span', 'checkout-address-badge', 'Alamat utama'));
                    copy.append(title, make('span', 'checkout-address-person', `${address.penerima || 'Penerima belum diisi'} · ${address.telepon || 'Telepon belum diisi'}`), make('span', 'checkout-address-text', [address.lengkap, address.kecamatan, address.kota, address.provinsi, address.kodePos].filter(Boolean).join(', ')));
                    if (!complete) copy.append(make('span', 'checkout-address-incomplete-note', 'Alamat belum lengkap. Lengkapi melalui Profil.'));
                    label.append(radio, copy); option.append(label); addressList.append(option);
                    radio.addEventListener('change', () => {
                        if (!radio.checked) return;
                        selectedAddressId = String(address.id);
                        addressList.querySelectorAll('.checkout-address-option').forEach(row => row.classList.toggle('is-selected', row.contains(radio)));
                        addressFeedback.hidden = true;
                        submit.disabled = false;
                    });
                });
                const selected = addresses.find(address => String(address.id) === String(selectedAddressId));
                if (!selected || !selected.penerima || !selected.telepon || !selected.kodePos || !selected.provinsi || !selected.kota || !selected.kecamatan || !selected.lengkap || selected.lengkap.trim().length < 10) {
                    selectedAddressId = null;
                    showError('Pilih alamat yang lengkap atau lengkapi alamat melalui Profil.');
                }
            }

            itemsNode.replaceChildren();
            let subtotal = 0;
            checkoutItems.forEach(item => {
                const qty = Number(item.jumlah || 1);
                const price = Number(item.harga || 0);
                subtotal += price * qty;
                const row = make('div', 'checkout-item');
                if (item.gambar) { const image = make('img'); image.src = item.gambar; image.alt = item.nama || 'Foto produk'; image.loading = 'lazy'; row.append(image); }
                else row.append(make('span', 'checkout-item-placeholder', '✧'));
                const copy = make('div', 'checkout-item-copy');
                copy.append(make('strong', '', item.nama || 'Produk Albis Antique'), make('small', '', `${qty} item × ${money(price)}`));
                row.append(copy, make('strong', 'checkout-item-price', money(price * qty)));
                itemsNode.append(row);
            });
            const ongkir = Number(data.ongkir || 0);   // dihitung server; total final tetap dihitung ulang server saat pesan
            const ongkirNode = document.getElementById('checkoutShipping');
            if (ongkirNode) ongkirNode.textContent = ongkir > 0 ? money(ongkir) : 'Gratis';
            subtotalNode.textContent = money(subtotal); totalNode.textContent = money(subtotal + ongkir);
            if (!checkoutItems.length) { form.hidden = true; empty.hidden = false; return; }
            empty.hidden = true; form.hidden = false;
            submit.disabled = !selectedAddressId || submit.dataset.midtransReady !== 'true';
        } catch (error) {
            form.hidden = true; empty.hidden = false;
            const message = make('p', '', error.message || 'Data checkout gagal dimuat.');
            empty.append(message);
            return;
        }

        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (!selectedAddressId) { showError('Pilih alamat yang lengkap sebelum membuat pesanan.'); return; }
            submit.disabled = true;
            const original = submit.textContent;
            submit.textContent = 'Menyimpan pesanan…';
            try {
                const payload = {
                    address_id: Number(selectedAddressId),
                    payment_method: document.getElementById('checkoutPayment').value,
                };
                if (directId) { payload.direct_product_id = directId; payload.quantity = directQuantity; }
                const result = await request('/customer/api/orders', 'POST', payload);
                const redirectUrl = String(result.redirectUrl || '');
                if (!redirectUrl.startsWith('https://')) throw new Error('Pesanan tersimpan, tetapi alamat pembayaran Midtrans tidak tersedia. Buka Riwayat Pesanan untuk mencoba lagi.');
                submit.textContent = 'Membuka Midtrans…';
                window.location.assign(redirectUrl);
            } catch (error) {
                showError(error.message || 'Pesanan gagal disimpan. Periksa stok dan alamat lalu coba lagi.');
            } finally {
                submit.disabled = !selectedAddressId || submit.dataset.midtransReady !== 'true';
                submit.textContent = original;
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('checkoutForm')) void mulaiCheckout();
    });
})();
