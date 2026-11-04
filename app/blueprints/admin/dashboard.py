"""Dashboard ringkasan admin."""
from flask import render_template

from app.services.report_service import LayananLaporan
from app.utils.decorators import admin_required
from . import admin_bp


@admin_bp.get("/")
@admin_required
def dashboard():
    """Tampilkan ringkasan awal; data dinamis disegarkan oleh admin.js."""
    ringkasan = LayananLaporan().buat_ringkasan(include_transactions=False)
    return render_template("admin/dashboard.html", ringkasan=ringkasan)
