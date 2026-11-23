"""Admin: audit log dan ganti kata sandi admin. (pemilik: Arga)"""
from __future__ import annotations
from datetime import datetime, timezone

from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_
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
    """Riwayat Application Audit Trail; Wazuh tetap menjadi console deteksi keamanan."""
    q = " ".join((request.args.get("q") or "").split())[:100]
    kategori = (request.args.get("kategori") or "").strip()[:40]
    hasil = (request.args.get("hasil") or "").strip()[:20]
    tingkat = (request.args.get("severity") or "").strip()[:12]
    try:
        page = max(1, min(int(request.args.get("page", 1)), 100000))
    except (TypeError, ValueError):
        page = 1

    query = AuditLog.query
    if kategori in {"authentication", "authorization", "administration", "commerce", "payment", "application"}:
        query = query.filter(AuditLog.event_category == kategori)
    else:
        kategori = ""
    if hasil in {"success", "failure", "blocked", "rejected", "flagged", "duplicate"}:
        query = query.filter(AuditLog.outcome == hasil)
    else:
        hasil = ""
    if tingkat in {"info", "low", "medium", "high", "critical"}:
        query = query.filter(AuditLog.severity == tingkat)
    else:
        tingkat = ""
    if q:
        pola = f"%{q.replace(chr(92), chr(92) * 2).replace('%', chr(92) + '%').replace('_', chr(92) + '_')}%"
        query = query.filter(or_(
            AuditLog.actor_email.ilike(pola, escape="\\"),
            AuditLog.action.ilike(pola, escape="\\"),
            AuditLog.event_action.ilike(pola, escape="\\"),
            AuditLog.target_type.ilike(pola, escape="\\"),
            AuditLog.target_id.ilike(pola, escape="\\"),
            AuditLog.detail.ilike(pola, escape="\\"),
            AuditLog.ip.ilike(pola, escape="\\"),
        ))

    pagination = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    hari_ini = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = AuditLog.query.count()
    aktivitas_admin = AuditLog.query.filter(AuditLog.event_category == "administration").count()
    peringatan = AuditLog.query.filter(
        AuditLog.severity.in_(["high", "critical"])
    ).count()
    hari_ini_total = AuditLog.query.filter(AuditLog.created_at >= hari_ini).count()

    return render_template(
        "admin/audit.html",
        baris=[row.to_dict() for row in pagination.items], pagination=pagination,
        q=q, kategori=kategori, hasil=hasil, tingkat=tingkat,
        total=total, aktivitas_admin=aktivitas_admin, peringatan=peringatan,
        hari_ini_total=hari_ini_total,
    )


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
