"""Admin: pesanan, pembayaran, moderasi ulasan. (pemilik: Intan)"""
from __future__ import annotations
from flask import jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from app.extensions import db
from app.models import Order, Payment
from app.services.order_service import LayananPesanan
from app.services.payment_service import LayananPembayaran
from app.services.review_service import LayananUlasan
from app.utils import audit
from . import admin_bp
from app.utils.decorators import admin_required


@admin_bp.get("/pesanan")
@admin_required
def pesanan():
    return render_template("admin/orders.html")


@admin_bp.get("/pembayaran")
@admin_required
def pembayaran():
    # Alias halaman gabungan pesanan & pembayaran; tab pembayaran dapat dibuka melalui hash.
    return render_template("admin/orders.html", buka_tab="pembayaran")


@admin_bp.get("/ulasan")
@admin_required
def ulasan():
    return render_template("admin/reviews.html")


@admin_bp.get("/api/pesanan")
@admin_required
def api_pesanan():
    LayananPesanan.kedaluwarsakan()
    return jsonify([o.to_dict() for o in Order.query.order_by(Order.created_at.desc()).all()])


@admin_bp.patch("/api/pesanan/<int:order_id>")
@admin_required
def api_ubah_status_pesanan(order_id: int):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Pesanan tidak ditemukan."), 404
    status = (request.get_json(silent=True) or {}).get("status")
    lama = order.status
    try:
        LayananPesanan.ubah_status(order, status, current_user)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422
    audit.catat("status_pesanan", "order", order.id, f"{order.order_number}: {lama} -> {order.status}", commit=True)
    return jsonify(message="Status pesanan diperbarui.", order=order.to_dict())


@admin_bp.get("/api/pembayaran")
@admin_required
def api_daftar_pembayaran():
    payments = Payment.query.order_by(Payment.uploaded_at.desc().nullslast(), Payment.id.desc()).all()
    return jsonify([p.to_dict() for p in payments])


@admin_bp.post("/api/pembayaran/<int:payment_id>/tinjau")
@admin_required
def api_tinjau_pembayaran(payment_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        payment = LayananPembayaran.tinjau(payment_id, current_user, payload.get("aksi", ""), payload.get("catatan", ""))
    except LookupError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 404
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422
    audit.catat("pembayaran_" + ("disetujui" if payment.status == "Disetujui" else "ditolak"), "payment", payment.id,
                payment.order.order_number, commit=True)
    return jsonify(message="Status pembayaran diperbarui.", payment=payment.to_dict())


@admin_bp.post("/api/pesanan/<int:order_id>/kirim-sertifikat")
@admin_required
def api_kirim_ulang_sertifikat(order_id: int):
    """Retry email sertifikat jika sebelumnya gagal atau sertifikat baru saja dilengkapi."""
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Pesanan tidak ditemukan."), 404
    from app.services.certificate_delivery_service import kirim_sertifikat_untuk_order
    hasil = kirim_sertifikat_untuk_order(order_id, retry_failed=True)
    audit.catat(
        "certificate_email_retry", "order", order_id,
        "Admin meminta percobaan pengiriman ulang sertifikat.",
        category="certificate", event_action="certificate.email.retry_requested",
        outcome="requested", severity="info", context={"result": hasil}, commit=True,
    )
    return jsonify(message="Permintaan pengiriman sertifikat diproses.", hasil=hasil, order_id=order_id)


@admin_bp.get("/api/ulasan")
@admin_required
def api_ulasan():
    return jsonify(LayananUlasan.semua_admin())


@admin_bp.post("/api/ulasan/<int:review_id>/moderasi")
@admin_required
def api_moderasi_ulasan(review_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        r = LayananUlasan.moderasi(review_id, current_user, bool(payload.get("sembunyikan")), payload.get("alasan", ""))
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422
    audit.catat("ulasan_disembunyikan" if r.is_hidden else "ulasan_ditampilkan", "review", r.id, r.hidden_reason or "", commit=True)
    return jsonify(message="Moderasi ulasan disimpan.", ulasan=LayananUlasan.semua_admin())
