"""Entitas akun dan alamat pelanggan."""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer", index=True)
    telepon = db.Column(db.String(20), nullable=False, default="")
    alamat_registrasi = db.Column(db.Text, nullable=True)
    avatar_data = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    auth_version = db.Column(db.Integer, nullable=False, default=1)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status_reason = db.Column(db.String(300), nullable=True)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    addresses = db.relationship("Address", back_populates="user", cascade="all, delete-orphan", order_by="Address.id")
    cart = db.relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = db.relationship("Order", back_populates="user", cascade="save-update, merge")
    reviews = db.relationship("Review", back_populates="user", cascade="all, delete-orphan", foreign_keys="Review.user_id")

    def get_id(self) -> str:
        # Versi otentikasi ikut di sesi: ganti password otomatis mencabut sesi lama.
        return f"{self.id}:{self.auth_version}"

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        self.auth_version = (self.auth_version or 1) + 1

    def cek_password(self, password: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)

    def check_password(self, password: str) -> bool:
        return self.cek_password(password)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def halaman_awal(self) -> str:
        return "admin.dashboard" if self.role == "admin" else "customer.dashboard"

    @property
    def alamat(self) -> str:
        primary = next((address for address in self.addresses if address.is_primary), None)
        if not primary and self.addresses:
            primary = self.addresses[0]
        return primary.ringkas if primary else (self.alamat_registrasi or "")

    @property
    def foto(self) -> str | None:
        return self.avatar_data

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} role={self.role}>"


class Address(db.Model):
    __tablename__ = "addresses"
    __table_args__ = (db.Index("ix_addresses_user_primary", "user_id", "is_primary"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = db.Column(db.String(30), nullable=False, default="Alamat")
    penerima = db.Column(db.String(100), nullable=False)
    telepon = db.Column(db.String(20), nullable=False)
    kode_pos = db.Column(db.String(5), nullable=False)
    provinsi = db.Column(db.String(100), nullable=False)
    kota = db.Column(db.String(100), nullable=False)
    kecamatan = db.Column(db.String(100), nullable=False)
    lengkap = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="addresses")

    @property
    def ringkas(self) -> str:
        return ", ".join(part for part in [self.lengkap, self.kecamatan, self.kota, self.provinsi, self.kode_pos] if part)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "label": self.label, "penerima": self.penerima,
            "telepon": self.telepon, "kodePos": self.kode_pos, "provinsi": self.provinsi,
            "kota": self.kota, "kecamatan": self.kecamatan, "lengkap": self.lengkap,
            "isPrimary": self.is_primary,
        }
