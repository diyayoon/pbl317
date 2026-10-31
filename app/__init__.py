"""Application factory Flask untuk Albis Antique (PostgreSQL: albis_db)."""
import logging
import os
from pathlib import Path

from flask import Flask, abort, send_file, send_from_directory
from flask_login import current_user

from .config import DevelopmentConfig, ProductionConfig
from .extensions import csrf, db, login_manager, migrate

_PLACEHOLDER_SECRET = (
    "hanya-untuk-development", "isi_secret", "replace_with", "change_me",
    "your_secret", "secret_key_here", "ganti",
)


def _validasi_konfigurasi(app: Flask) -> None:
    if app.config.get("TESTING"):
        return
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL wajib diisi (contoh: postgresql+psycopg://user:pass@host:5432/albis_db).")
    uri = str(app.config["SQLALCHEMY_DATABASE_URI"])
    if uri.startswith("sqlite"):
        # Hanya untuk preview/pengembangan di laptop; data tidak sama dengan PostgreSQL.
        if app.config.get("APP_ENV") != "development":
            raise RuntimeError("SQLite hanya boleh dipakai dengan APP_ENV=development. Production wajib PostgreSQL (albis_db).")
        app.logger.warning("Mode SQLite lokal aktif (khusus development). Produksi memakai PostgreSQL.")
    elif not uri.startswith("postgresql"):
        raise RuntimeError("Database tidak didukung. Pakai PostgreSQL (albis_db), atau SQLite hanya untuk development lokal.")
    if app.config.get("APP_ENV") == "production":
        secret = str(app.config.get("SECRET_KEY") or "").strip()
        if len(secret) < 32 or any(m in secret.lower() for m in _PLACEHOLDER_SECRET):
            raise RuntimeError("Production membutuhkan SECRET_KEY acak minimal 32 karakter; nilai contoh/placeholder tidak boleh digunakan.")
        # Mode Midtrans hanya ditentukan MIDTRANS_IS_PRODUCTION; awalan kunci tidak andal untuk membedakan sandbox/production.
        # Tautan email dibuat dari nilai ini, bukan header Host (anti Host header injection).
        if not str(app.config.get("APP_BASE_URL") or "").startswith(("http://", "https://")):
            raise RuntimeError("Production membutuhkan APP_BASE_URL (mis. https://domain-anda) untuk tautan verifikasi email.")


def buat_app(konfigurasi=None):
    """Membuat aplikasi Flask; tidak membuat/mengubah schema otomatis."""
    app = Flask(__name__)
    if konfigurasi is None:
        env = os.getenv("APP_ENV", "development").strip().lower()
        konfigurasi = ProductionConfig if env == "production" else DevelopmentConfig
    app.config.from_object(konfigurasi)
    _validasi_konfigurasi(app)

    # Satu handler saja (log Flask ke stderr/stdout container); tanpa basicConfig agar tidak ganda.
    app.logger.setLevel(logging.INFO)

    db.init_app(app)
    from . import models  # noqa: F401  (metadata untuk Flask-Migrate)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .security import init_security
    init_security(app)
    from .sesi import init_sesi
    init_sesi(app)
    from .kedaluwarsa import init_kedaluwarsa
    init_kedaluwarsa(app)

    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.customer import customer_bp
    from .blueprints.admin import admin_bp
    from .blueprints.midtrans import midtrans_bp
    for bp in (main_bp, auth_bp, customer_bp, admin_bp, midtrans_bp):
        app.register_blueprint(bp)

    @app.context_processor
    def _konteks_pembayaran():
        from .services.midtrans_service import aktif
        return {"midtrans_aktif": aktif()}

    from .commands import register_commands
    register_commands(app)

    @app.get("/health")
    def health():
        # Sengaja tidak menyentuh database: dipakai healthcheck container.
        return {"status": "ok"}, 200

    @app.get("/health/db")
    def health_db():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "up"}, 200
        except Exception:
            db.session.rollback()
            return {"status": "degraded", "database": "down"}, 503

    @app.get("/media/products/<path:nama_file>")
    def media_produk(nama_file):
        folder = Path(app.config["PRODUCT_UPLOAD_FOLDER"]).resolve()
        target = (folder / nama_file).resolve()
        if folder not in target.parents or not target.is_file():
            abort(404)
        return send_from_directory(folder, nama_file, conditional=True)

    @app.get("/media/categories/<path:nama_file>")
    def media_kategori(nama_file):
        folder = Path(app.config["CATEGORY_UPLOAD_FOLDER"]).resolve()
        target = (folder / nama_file).resolve()
        if folder not in target.parents or not target.is_file():
            abort(404)
        return send_from_directory(folder, nama_file, conditional=True)

    @app.get("/media/avatars/<path:nama_file>")
    def media_avatar(nama_file):
        from .models import User

        if Path(nama_file).name != nama_file:
            abort(404)
        referensi = f"/media/avatars/{nama_file}"
        pengguna = User.query.filter_by(
            avatar_data=referensi, is_active=True, deleted_at=None
        ).first()
        if pengguna is None:
            abort(404)
        if not current_user.is_authenticated or current_user.id != pengguna.id:
            from .models import Review
            if not Review.query.filter_by(user_id=pengguna.id, is_hidden=False).first():
                abort(404)

        folder = Path(app.config["AVATAR_UPLOAD_FOLDER"]).resolve()
        target = (folder / nama_file).resolve()
        if folder not in target.parents or not target.is_file():
            abort(404)
        return send_from_directory(folder, nama_file, conditional=True)

    @app.get("/media/reviews/<int:review_id>")
    def media_ulasan(review_id):
        """Foto ulasan publik hanya tersedia bila ulasan tidak disembunyikan admin."""
        from .models import Review
        ulasan = db.session.get(Review, review_id)
        if not ulasan or ulasan.is_hidden or not ulasan.image_path:
            abort(404)
        path = Path(ulasan.image_path).resolve()
        base = Path(app.config["REVIEW_UPLOAD_FOLDER"]).resolve()
        if base not in path.parents or not path.is_file():
            abort(404)
        return send_file(path, conditional=True, as_attachment=False)

    @app.get("/media/payments/<int:payment_id>")
    def media_pembayaran(payment_id):
        """Bukti bayar hanya untuk pemilik pesanan atau admin; dicari lewat ID, bukan nama file."""
        from .models import Payment
        if not current_user.is_authenticated:
            abort(403)
        payment = db.session.get(Payment, payment_id)
        if not payment or not payment.proof_path:
            abort(404)
        if current_user.role != "admin" and payment.order.user_id != current_user.id:
            abort(403)
        path = Path(payment.proof_path).resolve()
        base = Path(app.config["PAYMENT_UPLOAD_FOLDER"]).resolve()
        if base not in path.parents or not path.is_file():
            abort(404)
        return send_file(path, as_attachment=True, download_name=payment.original_filename or path.name)

    return app
