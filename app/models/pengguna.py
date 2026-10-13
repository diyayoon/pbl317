"""Model akun: users, addresses, audit_logs."""
from flask_login import UserMixin
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


class Pengguna(UserMixin, db.Model):
    """Akun admin/customer. Hash password tidak pernah dikeluarkan ke template/JSON."""
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('uq_users_username_lower', func.lower(db.column('username')), unique=True),
        db.Index('uq_users_email_lower', func.lower(db.column('email')), unique=True),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    tanggal_lahir = db.Column(db.Date)
    telepon = db.Column(db.String(15))
    role = db.Column(db.String(10), nullable=False, default='customer', server_default='customer')
    avatar_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    alamat = db.relationship('Alamat', back_populates='pengguna', cascade='all, delete-orphan')
    keranjang = db.relationship('Keranjang', back_populates='pengguna', uselist=False, cascade='all, delete-orphan')
    pesanan = db.relationship('Pesanan', back_populates='pengguna')

    # Flask-Login memakai get_id() sebagai string; user_loader memakai int(user_id).
    def set_password(self, password_polos):
        self.password_hash = generate_password_hash(password_polos)

    def cek_password(self, password_polos):
        return check_password_hash(self.password_hash, password_polos)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def halaman_awal(self):
        """Endpoint tujuan setelah login (polimorfisme sederhana berdasarkan role)."""
        return 'admin.dashboard' if self.is_admin else 'customer.dashboard'

    def __repr__(self):
        return f'<Pengguna {self.username} ({self.role})>'


class Alamat(db.Model):
    __tablename__ = 'addresses'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    label = db.Column(db.String(30), nullable=False, default='Rumah', server_default='Rumah')
    nama_penerima = db.Column(db.String(100), nullable=False)
    telepon = db.Column(db.String(15), nullable=False)
    alamat_lengkap = db.Column(db.String(255), nullable=False)
    kota = db.Column(db.String(100))
    provinsi = db.Column(db.String(100))
    kode_pos = db.Column(db.String(10))
    is_default = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    pengguna = db.relationship('Pengguna', back_populates='alamat')


class AuditLog(db.Model):
    """Catatan kejadian keamanan (SR-14)."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='SET NULL'), index=True)
    aksi = db.Column(db.String(50), nullable=False)
    target_tipe = db.Column(db.String(30))
    target_id = db.Column(db.BigInteger)
    ip_address = db.Column(db.String(45))
    detail = db.Column(JSONB)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
