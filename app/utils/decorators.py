"""Decorator keamanan untuk pembatasan role."""

from functools import wraps

from flask import abort, jsonify
from flask_login import current_user, login_required


def role_required(*role_yang_diizinkan):
    """Membatasi route agar hanya role tertentu yang dapat mengaksesnya."""

    def decorator(fungsi):
        @wraps(fungsi)
        def pembungkus(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.role not in role_yang_diizinkan:
                abort(403)
            return fungsi(*args, **kwargs)

        return pembungkus

    return decorator


def admin_required(fungsi):
    """Wajib login dan role admin (dipakai semua route /admin)."""
    return login_required(role_required("admin")(fungsi))


def terverifikasi_required(fungsi):
    """Aksi sensitif customer (pesan, bayar, ulasan) menuntut email terverifikasi; dicek di backend."""
    @wraps(fungsi)
    def pembungkus(*args, **kwargs):
        if current_user.role == "customer" and not current_user.is_verified:
            return jsonify(error="Verifikasi email Anda terlebih dahulu untuk melanjutkan.", perluVerifikasi=True), 403
        return fungsi(*args, **kwargs)
    return pembungkus
