"""Admin: dashboard dan laporan."""
from __future__ import annotations
from flask import jsonify, render_template
from app.services.report_service import LayananLaporan
from . import admin_bp
from app.utils.decorators import admin_required


@admin_bp.get("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", ringkasan=LayananLaporan().buat_ringkasan())


@admin_bp.get("/laporan")
@admin_required
def laporan():
    return render_template("admin/reports.html")


@admin_bp.get("/api/laporan")
@admin_required
def api_laporan():
    return jsonify(LayananLaporan().buat_ringkasan())
