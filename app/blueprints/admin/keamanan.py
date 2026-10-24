"""Admin: audit log dan ganti kata sandi admin. (pemilik: Arga)"""
from __future__ import annotations
from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user
from app.extensions import db
from app.models import AuditLog, User
from app.services.account_service import LayananAkun
from app.services.sesi_service import LayananSesi
from . import admin_bp
from app.utils.decorators import admin_required


@admin_bp.get("/audit")
@admin_required
def audit_log():
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(300).all()
    return render_template("admin/audit.html", baris=[r.to_dict() for r in rows])


@admin_bp.route("/akun", methods=["GET", "POST"])
@admin_required
def akun():
    if request.method == "POST":
        user = db.session.get(User, current_user.id)
        try:
            LayananAkun.ganti_password(
                user, request.form.get("password_lama", ""), request.form.get("password_baru", ""),
                request.form.get("konfirmasi_password", ""),
            )
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            LayananSesi.cabut_semua(user.id)
            session.clear()
            login_user(user)
            LayananSesi.mulai(user)
            flash("Kata sandi admin diperbarui. Sesi di perangkat lain telah dikeluarkan.", "success")
            return redirect(url_for("admin.akun"))
    return render_template("admin/account.html")
