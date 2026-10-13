"""Autentikasi akun demo lokal, tanpa database (khusus development)."""
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from app.utils.validasi import ValidasiRegistrasi
from . import auth_bp


class DemoUser:
    """Objek user sementara agar Flask-Login bisa dipakai tanpa model/database."""
    def __init__(self, user_id, email, nama, role):
        self.id = user_id
        self.email = email
        self.nama = nama
        self.role = role
        self.is_active = True
        self.is_authenticated = True
        self.is_anonymous = False

    def get_id(self):
        return self.id

    def __repr__(self):
        return f"<DemoUser {self.email} ({self.role})>"


# Akun demo hanya untuk pengujian lokal. Tidak digunakan untuk production.
DEMO_ACCOUNTS = {
    'customer@albis.local': {'password': 'AlbisCustomer123!', 'id': 'demo-customer', 'nama': 'Albis Collector', 'role': 'customer'},
    'admin@albis.local': {'password': 'AlbisAdmin123!', 'id': 'demo-admin', 'nama': 'Albis Administrator', 'role': 'admin'},
}
DEMO_BY_ID = {
    data['id']: DemoUser(data['id'], email, data['nama'], data['role'])
    for email, data in DEMO_ACCOUNTS.items()
}


def muat_demo_user(user_id):
    """Mengembalikan akun demo berdasarkan ID sesi; tidak menyentuh database."""
    if not current_app.config.get('DEMO_AUTH_ENABLED', False):
        return None
    return DEMO_BY_ID.get(user_id)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login akun demo sementara selama backend database belum diintegrasikan."""
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard' if current_user.role == 'admin' else 'customer.dashboard'))

    if request.method == 'POST':
        if not current_app.config.get('DEMO_AUTH_ENABLED', False):
            flash('Login demo dinonaktifkan. Integrasikan autentikasi database terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login'))
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        akun = DEMO_ACCOUNTS.get(email)
        if akun and password == akun['password']:
            user = DEMO_BY_ID[akun['id']]
            login_user(user, remember=bool(request.form.get('remember')))
            next_url = request.args.get('next')
            # Hindari redirect ke URL eksternal dari parameter next.
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect(url_for('admin.dashboard' if user.role == 'admin' else 'customer.dashboard'))
        flash('Email atau kata sandi demo tidak sesuai.', 'danger')
    return render_template('auth/login.html', demo_auth_enabled=current_app.config.get('DEMO_AUTH_ENABLED', False))


@auth_bp.get('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.beranda'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registrasi tetap berupa prototipe sampai penyimpanan database tersedia."""
    nilai, galat = {}, {}
    if request.method == 'POST':
        nilai, galat = ValidasiRegistrasi(request.form).periksa()
        if not galat:
            flash('Registrasi belum menyimpan akun. Untuk sementara, gunakan akun demo di halaman login.', 'info')
            return redirect(url_for('auth.login'))
    status = 422 if galat else 200
    return render_template('auth/register.html', nilai=nilai, galat=galat), status
