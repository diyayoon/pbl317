"""Extension Flask yang dipakai bersama oleh seluruh aplikasi."""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate(compare_type=True)
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan login terlebih dahulu."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"


@login_manager.user_loader
def memuat_pengguna(user_id: str):
    """ID sesi berbentuk '<id>:<auth_version>'; versi lama (setelah ganti password) ditolak."""
    from .models import User
    try:
        uid, _, versi = str(user_id).partition(":")
        user = db.session.get(User, int(uid))
        if user is None or not user.is_active or str(user.auth_version) != versi:
            return None
        return user
    except (TypeError, ValueError):
        return None


@login_manager.unauthorized_handler
def tidak_terautentikasi():
    """API mendapat JSON 401; halaman biasa diarahkan ke login."""
    from flask import jsonify, redirect, request, url_for
    if "/api/" in request.path:
        return jsonify(error="Sesi berakhir. Silakan login kembali.", login=url_for("auth.login")), 401
    return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
