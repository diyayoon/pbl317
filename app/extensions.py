"""Extension Flask yang dipakai bersama oleh seluruh aplikasi."""

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan login terlebih dahulu."
login_manager.login_message_category = "warning"


# ===== LOADER PENGGUNA SEMENTARA =====
# Versi frontend belum mengaktifkan model User. Callback ini mencegah Flask-Login
# melempar error saat template mengakses current_user. Saat model User sudah jadi,
# ganti isi fungsi ini dengan query user berdasarkan ID dari database.
@login_manager.user_loader
def memuat_pengguna(user_id):
    # Import di dalam callback menghindari circular import saat aplikasi dibuat.
    from .blueprints.auth.routes import muat_demo_user
    return muat_demo_user(user_id)
