"""Pencatatan aktivitas penting ke tabel audit_logs dan log aplikasi (OWASP A09)."""
from flask import current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import AuditLog
from .network import client_ip


def catat(aksi: str, target_type: str = "", target_id="", detail: str = "", actor=None, email: str = "", commit: bool = False):
    """Tambahkan satu baris audit. Secara default ikut transaksi pemanggil."""
    user = actor
    if user is None and getattr(current_user, "is_authenticated", False):
        user = current_user
    entry = AuditLog(
        actor_id=getattr(user, "id", None), actor_email=(getattr(user, "email", "") or email)[:254],
        action=aksi[:60], target_type=target_type[:40], target_id=str(target_id)[:60],
        detail=str(detail)[:500], ip=client_ip(),
    )
    db.session.add(entry)
    current_app.logger.info("audit aksi=%s aktor=%s target=%s:%s ip=%s", aksi, entry.actor_email or "-", target_type, target_id, entry.ip)
    if commit:
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Audit log gagal disimpan.")
