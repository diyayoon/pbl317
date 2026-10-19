"""Admin: dashboard, pengguna, laporan. (pemilik: Intan)"""
from __future__ import annotations
from flask import jsonify, render_template
from app.models import User
from app.services.order_service import LayananPesanan
from app.services.report_service import LayananLaporan
from . import admin_bp
from app.utils.decorators import admin_required


@admin_bp.get("/")
@admin_required
def dashboard():
    LayananPesanan.kedaluwarsakan()
    return render_template("admin/dashboard.html", ringkasan=LayananLaporan().buat_ringkasan())


@admin_bp.get("/pengguna")
@admin_required
def pengguna():
    rows = [
        {"email": u.email, "nama": u.nama, "role": u.role, "telepon": u.telepon,
         "status": "Aktif" if u.is_active else "Nonaktif", "bergabung": u.created_at.strftime("%d %b %Y")}
        for u in User.query.order_by(User.role.asc(), User.nama.asc()).all()
    ]
    return render_template("admin/users.html", pengguna_list=rows)


@admin_bp.get("/laporan")
@admin_required
def laporan():
    return render_template("admin/reports.html")


@admin_bp.get("/api/laporan")
@admin_required
def api_laporan():
    LayananPesanan.kedaluwarsakan()
    return jsonify(LayananLaporan().buat_ringkasan())
