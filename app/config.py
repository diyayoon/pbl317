"""Konfigurasi Albis Antique. Aplikasi hanya berjalan di atas PostgreSQL (albis_db)."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def normalisasi_database_url(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    for lama in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
        if value.startswith(lama):
            return "postgresql+psycopg://" + value[len(lama):]
    return value


def _bool(nama: str, bawaan: bool) -> bool:
    mentah = os.getenv(nama)
    if mentah is None:
        return bawaan
    return mentah.strip().lower() in {"1", "true", "yes", "on"}


def _int(nama: str, bawaan: int) -> int:
    try:
        return int(os.getenv(nama, bawaan))
    except (TypeError, ValueError):
        return bawaan


_APP_ENV = os.getenv("APP_ENV", "development").strip().lower()


class Config:
    APP_ENV = _APP_ENV
    SECRET_KEY = os.getenv("SECRET_KEY", "hanya-untuk-development-lokal-ganti-di-env")
    SQLALCHEMY_DATABASE_URI = normalisasi_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 1800}

    # Upload
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
    UPLOAD_FOLDER = str(BASE_DIR / "instance" / "uploads")
    PAYMENT_UPLOAD_FOLDER = str(BASE_DIR / "instance" / "uploads" / "payments")
    PRODUCT_UPLOAD_FOLDER = str(BASE_DIR / "instance" / "uploads" / "products")
    PRODUCT_MAX_BYTES = 2 * 1024 * 1024
    CATEGORY_UPLOAD_FOLDER = str(BASE_DIR / "instance" / "uploads" / "categories")
    REVIEW_UPLOAD_FOLDER = str(BASE_DIR / "instance" / "uploads" / "reviews")
    AVATAR_UPLOAD_FOLDER = str(BASE_DIR / "instance" / "uploads" / "avatars")
    CATEGORY_MAX_BYTES = 3 * 1024 * 1024
    REVIEW_MAX_BYTES = 3 * 1024 * 1024
    PAYMENT_MAX_BYTES = 5 * 1024 * 1024
    AVATAR_MAX_BYTES = 1024 * 1024
    PAYMENT_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}

    # Sesi & cookie (OWASP A07)
    SESSION_COOKIE_NAME = "albis_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 14
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]

    # Anti brute-force (MITRE T1110): batas kegagalan per jendela waktu
    LOGIN_MAX_PER_EMAIL = _int("LOGIN_MAX_PER_EMAIL", 5)
    LOGIN_MAX_PER_IP = _int("LOGIN_MAX_PER_IP", 25)
    LOGIN_WINDOW_MENIT = _int("LOGIN_WINDOW_MENIT", 15)
    REGISTER_MAX_PER_IP = _int("REGISTER_MAX_PER_IP", 10)
    REGISTER_WINDOW_MENIT = _int("REGISTER_WINDOW_MENIT", 60)

    # Timeout inaktivitas (menit) ditegakkan di server. Admin sengaja lebih ketat.
    SESI_INAKTIF_MENIT_CUSTOMER = _int("SESI_INAKTIF_MENIT_CUSTOMER", 10)
    SESI_INAKTIF_MENIT_ADMIN = _int("SESI_INAKTIF_MENIT_ADMIN", 5)
    SESI_MAKS_MENIT = _int("SESI_MAKS_MENIT", 480)   # batas mutlak sejak login
    SESI_SENTUH_DETIK = _int("SESI_SENTUH_DETIK", 10)  # jeda minimum antar penulisan last_activity

    # Midtrans (Snap Redirect). Kunci hanya dari environment; kosong = metode Midtrans nonaktif.
    MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY", "").strip()
    MIDTRANS_IS_PRODUCTION = _bool("MIDTRANS_IS_PRODUCTION", False)

    # Aturan bisnis
    ORDER_PAYMENT_TTL_JAM = _int("ORDER_PAYMENT_TTL_JAM", 24)
    # Kedaluwarsa pesanan dijalankan berkala di dalam aplikasi (detik; 0 = nonaktif, pakai `flask expire-orders` terjadwal).
    ORDER_EXPIRE_INTERVAL_DETIK = _int("ORDER_EXPIRE_INTERVAL_DETIK", 60)
    # Ongkir tarif tetap (rupiah). SHIPPING_FREE_ABOVE > 0: gratis ongkir bila subtotal mencapai nilai itu.
    SHIPPING_COST_FLAT = _int("SHIPPING_COST_FLAT", 25000)
    SHIPPING_FREE_ABOVE = _int("SHIPPING_FREE_ABOVE", 0)
    MAX_OPEN_ORDERS = _int("MAX_OPEN_ORDERS", 5)

    # Verifikasi email & SMTP (kredensial hanya dari environment)
    EMAIL_VERIFY_TTL_JAM = _int("EMAIL_VERIFY_TTL_JAM", 24)
    EMAIL_VERIFY_COOLDOWN_DETIK = _int("EMAIL_VERIFY_COOLDOWN_DETIK", 60)
    EMAIL_VERIFY_MAX_PER_JAM = _int("EMAIL_VERIFY_MAX_PER_JAM", 5)
    EMAIL_VERIFY_KODE_DIGIT = _int("EMAIL_VERIFY_KODE_DIGIT", 6)      # 4-8; makin pendek makin mudah ditebak
    EMAIL_VERIFY_KODE_MAX_SALAH = _int("EMAIL_VERIFY_KODE_MAX_SALAH", 5)
    APP_BASE_URL = os.getenv("APP_BASE_URL", "").rstrip("/")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = _int("MAIL_PORT", 587)
    MAIL_SECURITY = os.getenv("MAIL_SECURITY", "starttls").strip().lower()  # starttls | ssl
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "")

    # Proxy (nginx -> gunicorn). Isi 1 bila di belakang satu reverse proxy.
    TRUSTED_PROXY_COUNT = _int("TRUSTED_PROXY_COUNT", 0)

    # Instruksi pembayaran toko (isi lewat environment, bukan hardcode)
    PAYMENT_BANK_NAME = os.getenv("PAYMENT_BANK_NAME", "")
    PAYMENT_BANK_ACCOUNT = os.getenv("PAYMENT_BANK_ACCOUNT", "")
    PAYMENT_BANK_HOLDER = os.getenv("PAYMENT_BANK_HOLDER", "")
    PAYMENT_QRIS_NOTE = os.getenv("PAYMENT_QRIS_NOTE", "")


class DevelopmentConfig(Config):
    DEBUG = _bool("FLASK_DEBUG", False)


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    ORDER_EXPIRE_INTERVAL_DETIK = 0   # test memicu kedaluwarsa secara eksplisit
    SECRET_KEY = "kunci-khusus-pengujian-otomatis-0123456789abcdef"
    LOGIN_MAX_PER_EMAIL = 5
    PAYMENT_UPLOAD_FOLDER = "/tmp/albis_test_uploads/payments"  # nosec B108 (hanya konfigurasi uji)
    PRODUCT_UPLOAD_FOLDER = "/tmp/albis_test_uploads/products"  # nosec B108
    CATEGORY_UPLOAD_FOLDER = "/tmp/albis_test_uploads/categories"  # nosec B108
    REVIEW_UPLOAD_FOLDER = "/tmp/albis_test_uploads/reviews"  # nosec B108
    AVATAR_UPLOAD_FOLDER = "/tmp/albis_test_uploads/avatars"  # nosec B108


class ProductionConfig(Config):
    APP_ENV = "production"
    DEBUG = False
    # Boleh dimatikan hanya untuk uji internal lewat HTTP (SESSION_COOKIE_SECURE=0).
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)
    REMEMBER_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)
    TRUSTED_PROXY_COUNT = _int("TRUSTED_PROXY_COUNT", 1)
