"""Admin: peninjauan, pengiriman, dan sinkronisasi permintaan refund Midtrans."""
from flask import jsonify, render_template, request
from flask_login import current_user
from app.extensions import db
from app.services.refund_service import ErrorRefund, LayananRefund
from app.services.midtrans_service import ErrorMidtrans
from app.utils.decorators import admin_required
from . import admin_bp


@admin_bp.get("/refund")
@admin_required
def refund():
    return render_template("admin/refunds.html")


@admin_bp.get("/api/refund")
@admin_required
def api_daftar_refund():
    return jsonify(LayananRefund.daftar_admin())


@admin_bp.post("/api/refund/<int:refund_id>/tinjau")
@admin_required
def api_tinjau_refund(refund_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        row = LayananRefund.tinjau(refund_id, current_user,
                                  str(payload.get("aksi", "")), str(payload.get("catatan", "")))
        return jsonify(message="Permintaan refund diperbarui.", refund=row.to_dict())
    except (ErrorRefund, ErrorMidtrans) as exc:
        db.session.rollback()
        return jsonify(error=getattr(exc, "pesan", str(exc))), getattr(exc, "kode", 502)


@admin_bp.post("/api/refund/<int:refund_id>/sinkron")
@admin_required
def api_sinkron_refund(refund_id: int):
    try:
        row = LayananRefund.sinkronkan(refund_id, current_user)
        return jsonify(message="Status refund diperbarui dari Midtrans.", refund=row.to_dict())
    except (ErrorRefund, ErrorMidtrans) as exc:
        db.session.rollback()
        return jsonify(error=getattr(exc, "pesan", str(exc))), getattr(exc, "kode", 502)
