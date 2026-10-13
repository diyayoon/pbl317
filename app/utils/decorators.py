"""Decorator keamanan untuk pembatasan role."""

from functools import wraps

from flask import abort
from flask_login import current_user


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
