"""Pabrik aplikasi Albis Antique.

Fokus versi ini adalah struktur frontend Jinja yang bersih, responsif, dan siap dikembangkan
ke backend PostgreSQL dengan pendekatan SSDLC. Database dan autentikasi produksi belum diaktifkan.
"""
from flask import Flask, render_template
from .config import DevelopmentConfig
from .extensions import csrf, db, login_manager, migrate

# ===== FUNGSI: MEMBUAT INSTANCE APLIKASI FLASK =====
def buat_app(konfigurasi=DevelopmentConfig):
    """Membuat aplikasi Flask dan mendaftarkan extension serta blueprint."""
    app = Flask(__name__)
    app.config.from_object(konfigurasi)

    # ===== INISIALISASI EXTENSION =====
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ===== REGISTRASI BLUEPRINT =====
    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.customer import customer_bp
    from .blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)

    # ===== ERROR HANDLER =====
    @app.errorhandler(403)
    def akses_ditolak(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def tidak_ditemukan(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def kesalahan_server(error):
        return render_template('errors/500.html'), 500

    return app
