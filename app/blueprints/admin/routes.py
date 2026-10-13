"""Route admin prototipe.

Pada tahap backend, seluruh route di blueprint ini wajib dilindungi autentikasi dan role admin.
"""

from pathlib import Path

from flask_login import login_required
from ...utils.decorators import role_required

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from ...utils.uploads import EKSTENSI_GAMBAR, ekstensi_file_diizinkan, nama_file_aman
from . import admin_bp


# ===== ROUTE: DASHBOARD ADMIN =====
@admin_bp.get('/')
@login_required
@role_required('admin')
def dashboard():
    ringkasan = {
        'produk': 120,
        'pengguna': 86,
        'pesanan': 34,
        'pendapatan': 28450000,
    }
    return render_template('admin/dashboard.html', ringkasan=ringkasan)


# ===== ROUTE: FORM PRODUK & UPLOAD FOTO PROTOTIPE =====
@admin_bp.route('/produk', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def produk():
    """Menampilkan form produk dan menyimpan foto contoh di luar folder static."""
    nama_file_tersimpan = None

    if request.method == 'POST':
        foto = request.files.get('foto_produk')
        if not foto or not foto.filename:
            flash('Pilih foto produk terlebih dahulu.', 'warning')
            return redirect(url_for('admin.produk'))

        if not ekstensi_file_diizinkan(foto.filename, EKSTENSI_GAMBAR):
            flash('Format foto harus JPG, JPEG, PNG, atau WEBP.', 'warning')
            return redirect(url_for('admin.produk'))

        folder_upload = Path(current_app.instance_path) / 'uploads' / 'products'
        folder_upload.mkdir(parents=True, exist_ok=True)
        nama_file_tersimpan = nama_file_aman(foto.filename)
        foto.save(folder_upload / nama_file_tersimpan)
        flash(
            'Foto produk berhasil diunggah untuk prototipe. Data produk belum disimpan ke database.',
            'success',
        )

    return render_template('admin/products.html', nama_file_tersimpan=nama_file_tersimpan)


# ===== ROUTE: MENAMPILKAN FOTO UPLOAD PROTOTIPE =====
@admin_bp.get('/uploads/produk/<path:nama_file>')
@login_required
@role_required('admin')
def foto_produk(nama_file):
    """Menyajikan foto prototipe dari instance/uploads/products."""
    folder_upload = Path(current_app.instance_path) / 'uploads' / 'products'
    return send_from_directory(folder_upload, nama_file)
