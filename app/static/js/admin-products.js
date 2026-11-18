'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('adminProductsApp');
    const body = document.getElementById('adminProductsBody');
    const form = document.getElementById('adminProductForm');
    const panel = document.getElementById('productFormPanel');
    const toggle = document.getElementById('toggleProductForm');
    const search = document.getElementById('adminProductSearch');

    if (!app || !body || !form || !panel || !toggle) return;

    const apiUrl = app.dataset.apiUrl;
    const apiItemBase = String(app.dataset.apiItemUrl || '').replace(/\/0$/, '');
    const csrfToken = document.getElementById('csrfToken')?.value || '';
    const money = value => `Rp${Number(value || 0).toLocaleString('id-ID')}`;
    const formatRupiah = value => Number(value || 0).toLocaleString('id-ID');
    const make = (tag, className = '', text = undefined) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };

    let products = [];
    let apiReady = false;
    let newImageFile = null;
    let previewUrl = '';
    let imageProcessing = false;
    let imageSelectionVersion = 0;


    const fieldIds = {
        nama: 'productName',
        kategori: 'productCategory',
        era: 'productEra',
        asal: 'productOrigin',
        kondisi: 'productCondition',
        material: 'productMaterial',
        autentikasi: 'productAuthenticity',
        harga: 'productPrice',
        stok: 'productStock',
        deskripsi: 'productDescription',
    };

    async function requestJSON(url, options = {}) {
        const headers = {
            Accept: 'application/json',
            ...(options.headers || {}),
        };

        const method = String(options.method || 'GET').toUpperCase();
        // FormData (multipart): biarkan browser mengisi Content-Type + boundary sendiri.
        if (options.body !== undefined && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }
        if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
            headers['X-CSRFToken'] = csrfToken;
        }

        const response = await fetch(url, {
            credentials: 'same-origin',
            ...options,
            headers,
        });
        const payload = await response.json().catch(() => ({}));

        if (!response.ok) {
            const error = new Error(payload.error || `Permintaan gagal (${response.status}).`);
            error.status = response.status;
            error.details = payload.errors || {};
            throw error;
        }

        return payload;
    }

    function showToast(message, type = 'status') {
        let toast = document.getElementById('adminToast');
        if (!toast) {
            toast = make('div', 'albis-toast');
            toast.id = 'adminToast';
            toast.setAttribute('role', type);
            toast.setAttribute('aria-live', 'polite');
            document.body.append(toast);
        }

        toast.textContent = message;
        toast.setAttribute('role', type);
        toast.classList.add('is-visible');
        window.clearTimeout(toast._timer);
        toast._timer = window.setTimeout(() => toast.classList.remove('is-visible'), 3500);
    }

    function showPanel(visible) {
        panel.hidden = !visible;
        toggle.setAttribute('aria-expanded', String(visible));
        if (visible) document.getElementById('productName')?.focus();
    }

    function clearErrors() {
        form.querySelectorAll('[data-product-error]').forEach(node => {
            node.hidden = true;
            node.textContent = '';
        });
        form.querySelectorAll('.is-invalid').forEach(node => {
            node.classList.remove('is-invalid');
            node.removeAttribute('aria-invalid');
        });
    }

    function renderErrors(errors = {}) {
        clearErrors();
        Object.entries(errors).forEach(([key, message]) => {
            const node = form.querySelector(`[data-product-error="${key}"]`);
            const input = document.getElementById(fieldIds[key]);
            if (node) {
                node.textContent = message;
                node.hidden = false;
            }
            if (input) {
                input.classList.add('is-invalid');
                input.setAttribute('aria-invalid', 'true');
            }
        });
        const firstKey = Object.keys(errors)[0];
        if (firstKey && fieldIds[firstKey]) document.getElementById(fieldIds[firstKey])?.focus();
    }

    function resetForm() {
        form.reset();
        document.getElementById('productId').value = '';
        document.getElementById('productFormTitle').textContent = 'Tambah produk antik';
        document.getElementById('saveProductButton').textContent = 'Simpan produk';
        document.getElementById('saveProductButton').disabled = !apiReady;
        document.getElementById('productImagePreview').replaceChildren();
        document.getElementById('productImagePreview').hidden = true;
        newImageFile = null;
        imageSelectionVersion += 1;
        imageProcessing = false;
        clearPreviewUrl();
        clearErrors();
    }

    function setForm(product = null) {
        resetForm();
        if (product) {
            Object.entries(fieldIds).forEach(([key, id]) => {
                const input = document.getElementById(id);
                if (input) input.value = key === 'harga' ? formatRupiah(product[key]) : (product[key] ?? '');
            });
            document.getElementById('productId').value = String(product.id);
            document.getElementById('productFormTitle').textContent = 'Edit produk antik';
            document.getElementById('saveProductButton').textContent = 'Simpan perubahan';
            showImagePreview(product.gambar || '', product.nama || 'produk');
        }
        showPanel(true);
    }

    function clearPreviewUrl() {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = '';
    }

    function showImagePreview(source, name) {
        const preview = document.getElementById('productImagePreview');
        preview.replaceChildren();
        preview.classList.remove('has-error');
        preview.hidden = !source;
        if (!source) return;

        const image = make('img');
        image.src = source;
        image.alt = `Pratinjau foto ${name}`;
        image.decoding = 'async';
        image.addEventListener('error', () => {
            preview.classList.add('has-error');
        }, { once: true });
        image.addEventListener('load', () => preview.classList.remove('has-error'), { once: true });
        preview.append(image);
    }

    function formatPriceInput() {
        const input = document.getElementById('productPrice');
        if (!input) return;
        const original = input.value;
        const cursor = input.selectionStart ?? original.length;
        const digitBeforeCursor = original.slice(0, cursor).replace(/\D/g, '').length;
        const digits = original.replace(/\D/g, '');
        const formatted = digits ? Number(digits).toLocaleString('id-ID') : '';
        input.value = formatted;

        let nextCursor = 0;
        let digitsSeen = 0;
        while (nextCursor < formatted.length && digitsSeen < digitBeforeCursor) {
            if (/\d/.test(formatted[nextCursor])) digitsSeen += 1;
            nextCursor += 1;
        }
        if (digitBeforeCursor === 0) nextCursor = 0;
        input.setSelectionRange(nextCursor, nextCursor);
    }

    function render() {
        const term = String(search?.value || '').trim().toLocaleLowerCase('id-ID');
        const visibleProducts = products.filter(product => {
            const searchable = [
                product.nama,
                product.kategori,
                product.era,
                product.asal,
            ].join(' ').toLocaleLowerCase('id-ID');
            return searchable.includes(term);
        });

        body.replaceChildren();
        if (!visibleProducts.length) {
            const row = make('tr');
            const cell = make('td', 'table-empty', 'Tidak ada produk yang cocok dengan pencarian.');
            cell.colSpan = 5;
            row.append(cell);
            body.append(row);
        }

        visibleProducts.forEach(product => {
            const row = make('tr');
            const productCell = make('td', 'admin-product-cell');
            const identity = make('div', 'admin-product-ident');
            const imageBox = make('span', 'admin-product-thumb', product.gambar ? '' : '✧');

            if (product.gambar) {
                const image = make('img');
                image.src = product.gambar;
                image.alt = '';
                image.loading = 'lazy';
                imageBox.append(image);
            }

            const copy = make('div', 'admin-product-copy');
            copy.append(
                make('strong', '', product.nama),
                make('small', '', `ID #${product.id} · ${product.material || 'Material belum diisi'}${product.is_active === false ? ' · NONAKTIF (tidak tampil di katalog)' : ''}`),
            );
            identity.append(imageBox, copy);
            productCell.append(identity);

            const category = make('td', 'admin-product-category', `${product.kategori}\n${product.era}`);
            const price = make('td', 'admin-product-price', money(product.harga));
            const stock = make('td', 'admin-product-stock', String(product.stok));
            if (Number(product.stok) === 0) stock.classList.add('stock-empty');
            else if (Number(product.stok) <= 2) stock.classList.add('stock-low');

            const actionCell = make('td', 'admin-product-actions-cell');
            const actionButtons = make('div', 'admin-product-actions');
            const edit = make('button', 'button button-secondary button-small', 'Edit');
            edit.type = 'button';
            edit.addEventListener('click', () => setForm(product));

            const remove = make('button', 'button button-danger button-small', 'Hapus');
            remove.type = 'button';
            remove.disabled = !apiReady;
            remove.addEventListener('click', async () => {
                if (!apiReady) return;
                if (!window.confirm(`Hapus ${product.nama}? Bila produk sudah pernah dipesan, produk hanya dinonaktifkan agar riwayat pesanan tetap utuh.`)) return;
                remove.disabled = true;
                try {
                    const result = await requestJSON(`${apiItemBase}/${product.id}`, { method: 'DELETE' });
                    products = result.products || [];
                    render();
                    showToast(result.message || 'Produk dihapus.');
                } catch (error) {
                    remove.disabled = false;
                    showToast(error.message || 'Produk tidak berhasil dihapus.', 'alert');
                }
            });

            const aktif = product.is_active !== false;
            const switcher = make('button', 'button button-secondary button-small', aktif ? 'Nonaktifkan' : 'Aktifkan');
            switcher.type = 'button';
            switcher.disabled = !apiReady;
            switcher.addEventListener('click', async () => {
                switcher.disabled = true;
                try {
                    const result = await requestJSON(`${apiItemBase}/${product.id}/status`, { method: 'POST', body: JSON.stringify({ aktif: !aktif }) });
                    products = result.products || [];
                    render();
                    showToast(result.message);
                } catch (error) {
                    switcher.disabled = false;
                    showToast(error.message || 'Status produk gagal diubah.', 'alert');
                }
            });

            actionButtons.append(edit, switcher, remove);
            actionCell.append(actionButtons);
            row.append(productCell, category, price, stock, actionCell);
            body.append(row);
        });

        const count = document.getElementById('adminProductsCount');
        if (count) count.textContent = String(products.length);
    }

    async function loadProducts() {
        try {
            const result = await requestJSON(apiUrl);
            products = Array.isArray(result) ? result : [];
            apiReady = true;
            document.getElementById('saveProductButton').disabled = false;
            render();
        } catch (error) {
            products = [];
            apiReady = false;
            document.getElementById('saveProductButton').disabled = true;
            render();
            showToast('Data produk belum dapat dimuat. Penyimpanan dinonaktifkan agar perubahan tidak terlihat berhasil padahal gagal.', 'alert',
            );
        }
    }

    async function buildImageFile(file) {
        if (typeof createImageBitmap !== 'function') return file;
        let bitmap;
        try {
            bitmap = await createImageBitmap(file);
        } catch {
            return file;
        }
        const maximumDimension = 1000;
        const scale = Math.min(1, maximumDimension / Math.max(bitmap.width, bitmap.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(bitmap.width * scale));
        canvas.height = Math.max(1, Math.round(bitmap.height * scale));

        const context = canvas.getContext('2d');
        if (!context) {
            bitmap.close();
            return file;
        }
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        bitmap.close();

        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.78));
        if (!blob) return file;
        const baseName = (file.name || 'foto').replace(/\.[^.]+$/, '') || 'foto';
        return new File([blob], `${baseName}.jpg`, { type: 'image/jpeg' });
    }

    function collectFormData() {
        return {
            nama: document.getElementById('productName').value.trim(),
            kategori: document.getElementById('productCategory').value,
            era: document.getElementById('productEra').value,
            asal: document.getElementById('productOrigin').value.trim(),
            kondisi: document.getElementById('productCondition').value,
            material: document.getElementById('productMaterial').value.trim(),
            autentikasi: document.getElementById('productAuthenticity').value,
            harga: Number(document.getElementById('productPrice').value.replace(/\D/g, '')),
            stok: document.getElementById('productStock').value === ''
                ? null
                : Number(document.getElementById('productStock').value),
            deskripsi: document.getElementById('productDescription').value.trim(),
        };
    }

    function buildMultipart(payload, oldProduct = null) {
        const data = new FormData();
        Object.entries(payload).forEach(([key, value]) => {
            data.append(key, value === null || value === undefined ? '' : String(value));
        });
        if (oldProduct?.sumber_gambar) data.append('sumber_gambar', oldProduct.sumber_gambar);
        if (newImageFile) data.append('gambar', newImageFile, newImageFile.name);
        return data;
    }

    function validateForm(payload) {
        const errors = {};
        if (payload.nama.length < 3) errors.nama = 'Nama produk minimal 3 karakter.';
        if (!payload.asal) errors.asal = 'Asal produk wajib diisi.';
        if (!payload.material) errors.material = 'Material produk wajib diisi.';
        if (!payload.deskripsi) errors.deskripsi = 'Deskripsi produk wajib diisi.';
        if (!Number.isInteger(payload.harga) || payload.harga < 1000) {
            errors.harga = 'Harga minimum Rp1.000 dan harus berupa angka bulat.';
        }
        if (!Number.isInteger(payload.stok) || payload.stok < 0) {
            errors.stok = 'Stok harus bilangan bulat nonnegatif.';
        }
        return errors;
    }

    toggle.addEventListener('click', () => {
        const isOpening = panel.hidden;
        if (isOpening) resetForm();
        showPanel(isOpening);
    });

    document.getElementById('cancelProductForm')?.addEventListener('click', () => {
        resetForm();
        showPanel(false);
    });

    document.getElementById('cancelProductFormBottom')?.addEventListener('click', () => {
        resetForm();
        showPanel(false);
    });

    search?.addEventListener('input', render);

    document.getElementById('productPrice')?.addEventListener('input', formatPriceInput);

    document.getElementById('productImage')?.addEventListener('change', async event => {
        const input = event.currentTarget;
        const file = input.files?.[0];
        const rawId = document.getElementById('productId').value;
        const oldProduct = rawId
            ? products.find(product => Number(product.id) === Number(rawId))
            : null;
        const version = ++imageSelectionVersion;
        const saveButton = document.getElementById('saveProductButton');

        newImageFile = null;
        imageProcessing = false;
        saveButton.disabled = !apiReady;
        clearPreviewUrl();
        if (!file) {
            showImagePreview(oldProduct?.gambar || '', oldProduct?.nama || 'produk');
            return;
        }

        const extension = file.name.split('.').pop()?.toLowerCase();
        const accepted = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type)
            || (!file.type && ['jpg', 'jpeg', 'png', 'webp'].includes(extension));
        if (!accepted || file.size > 2 * 1024 * 1024) {
            input.value = '';
            showImagePreview(oldProduct?.gambar || '', oldProduct?.nama || 'produk');
            showToast('Pilih JPG, PNG, atau WEBP dengan ukuran maksimal 2 MB.', 'alert');
            return;
        }

        previewUrl = URL.createObjectURL(file);
        showImagePreview(previewUrl, file.name);
        imageProcessing = true;
        saveButton.disabled = true;
        try {
            newImageFile = await buildImageFile(file);
            if (version !== imageSelectionVersion) return;
        } catch (error) {
            if (version !== imageSelectionVersion) return;
            newImageFile = file;
            showToast('Foto akan diunggah tanpa kompresi tambahan.', 'status');
        } finally {
            if (version === imageSelectionVersion) {
                imageProcessing = false;
                saveButton.disabled = !apiReady;
            }
        }
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!apiReady) {
            showToast('Sumber data belum siap. Perubahan belum disimpan.', 'alert');
            return;
        }
        if (imageProcessing) {
            showToast('Tunggu sampai foto selesai diproses.', 'alert');
            return;
        }

        const saveButton = document.getElementById('saveProductButton');
        if (saveButton.disabled) return;

        const rawId = document.getElementById('productId').value;
        const oldProduct = rawId
            ? products.find(product => Number(product.id) === Number(rawId))
            : null;
        const payload = collectFormData();
        const clientErrors = validateForm(payload);
        clearErrors();
        if (Object.keys(clientErrors).length) {
            renderErrors(clientErrors);
            return;
        }

        saveButton.disabled = true;
        saveButton.textContent = oldProduct ? 'Menyimpan perubahan…' : 'Menyimpan produk…';
        try {
            const response = await requestJSON(
                oldProduct ? `${apiItemBase}/${oldProduct.id}` : apiUrl,
                {
                    method: oldProduct ? 'PUT' : 'POST',
                    body: buildMultipart(payload, oldProduct),
                },
            );
            products = response.products || [];
            render();
            resetForm();
            showPanel(false);
            showToast(
                oldProduct
                    ? 'Perubahan produk tersimpan dan tampil di katalog.'
                    : 'Produk berhasil ditambahkan dan akan tampil di katalog.',
            );
        } catch (error) {
            if (error.details && Object.keys(error.details).length) {
                renderErrors(error.details);
            }
            showToast(error.message || 'Produk tidak berhasil disimpan.', 'alert');
        } finally {
            saveButton.disabled = !apiReady;
            saveButton.textContent = document.getElementById('productId').value
                ? 'Simpan perubahan'
                : 'Simpan produk';
        }
    });

    loadProducts();
});
