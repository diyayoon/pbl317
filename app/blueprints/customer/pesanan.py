"""Customer: riwayat pesanan, bukti bayar, ulasan. (pemilik: Intan)"""
from flask import current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Order, RefundRequest
from app.services.midtrans_service import ErrorMidtrans, LayananMidtrans
from app.services.order_service import LayananPesanan
from app.services.payment_service import LayananPembayaran
from app.services.review_service import LayananUlasan
from app.utils import audit
from app.utils.decorators import role_required, terverifikasi_required
from . import customer_bp



def _info_pembayaran() -> dict:
    cfg = current_app.config
    return {
        "bank": cfg.get("PAYMENT_BANK_NAME", ""), "rekening": cfg.get("PAYMENT_BANK_ACCOUNT", ""),
        "atasNama": cfg.get("PAYMENT_BANK_HOLDER", ""), "catatanQris": cfg.get("PAYMENT_QRIS_NOTE", ""),
        "batasJam": cfg.get("ORDER_PAYMENT_TTL_JAM", 24),
    }


@customer_bp.get("/pesanan")
@login_required
@role_required("customer")
def pesanan():
    return render_template("customer/orders.html", info_pembayaran=_info_pembayaran())


@customer_bp.get("/api/orders")
@login_required
@role_required("customer")
def api_orders():
    LayananPesanan.kedaluwarsakan()
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    ulasan = LayananUlasan.milik_user(current_user)
    hasil = []
    for order in orders:
        data = order.to_dict()
        refund = RefundRequest.query.filter_by(order_id=order.id).order_by(RefundRequest.requested_at.desc(), RefundRequest.id.desc()).first()
        data["refund"] = refund.to_dict() if refund else None
        data["paymentType"] = order.payment.gateway_payment_type if order.payment else ""
        for item in data["items"]:
            item["ulasanSaya"] = ulasan.get(item["orderItemId"])
            item["bisaUlas"] = bool(
                order.status == "Selesai" and item["id"] is not None
                and not item["ulasanSaya"] and LayananUlasan.bisa_direview(current_user, item["orderItemId"])
            )
        hasil.append(data)
    return jsonify(hasil)


@customer_bp.post("/api/orders/<int:order_id>/batal")
@login_required
@role_required("customer")
def api_batalkan_pesanan(order_id: int):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if order is None:
        return jsonify(error="Pesanan tidak ditemukan."), 404
    midtrans = order.payment_method == "Midtrans" and order.payment is not None and bool(order.payment.snap_redirect_url)
    try:
        if midtrans:   # pastikan belum terbayar sebelum dibatalkan; bila Midtrans tidak terjangkau, jangan batalkan
            if LayananMidtrans.sinkron(order) in ("lunas", "perlu_penanganan"):
                db.session.refresh(order)
                return jsonify(error="Pembayaran pesanan ini sudah diterima, jadi tidak bisa dibatalkan."), 409
        LayananPesanan.batalkan_oleh_customer(order_id, current_user)
    except ErrorMidtrans as exc:
        db.session.rollback()
        return jsonify(error=exc.pesan), exc.kode
    except LookupError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 404
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 409
    if midtrans:
        LayananMidtrans.batalkan_di_midtrans(order)
    return jsonify(ok=True, status="Dibatalkan")


@customer_bp.post("/api/orders/<int:order_id>/refund")
@login_required
@role_required("customer")
@terverifikasi_required
def api_ajukan_refund(order_id: int):
    from app.services.refund_service import ErrorRefund, LayananRefund
    payload = request.get_json(silent=True) or {}
    try:
        refund = LayananRefund.ajukan(order_id, current_user, str(payload.get("alasan", "")))
        return jsonify(message="Permintaan refund berhasil dikirim dan menunggu peninjauan admin.", refund=refund.to_dict()), 201
    except ErrorRefund as exc:
        db.session.rollback()
        return jsonify(error=exc.pesan), exc.kode
    except ErrorMidtrans as exc:
        db.session.rollback()
        return jsonify(error=exc.pesan), exc.kode


@customer_bp.post("/api/orders/<int:order_id>/bukti")
@login_required
@role_required("customer")
@terverifikasi_required
def api_upload_payment_proof(order_id: int):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order:
        return jsonify(error="Pesanan tidak ditemukan."), 404
    try:
        file = request.files.get("buktiBayar") or request.files.get("file")
        payment = LayananPembayaran(current_user).simpan_bukti(order, file)
        audit.catat("bukti_bayar_diunggah", "order", order.id, order.order_number, commit=True)
        return jsonify(message="Bukti pembayaran diunggah dan menunggu pemeriksaan admin.", payment=payment.to_dict()), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 422
    except LookupError as exc:
        return jsonify(error=str(exc)), 404


@customer_bp.post("/api/reviews")
@login_required
@role_required("customer")
@terverifikasi_required
def api_save_review():
    payload = request.form.to_dict() if request.mimetype == "multipart/form-data" else request.get_json(silent=True)
    image_file = request.files.get("gambarUlasan")
    try:
        ulasan = LayananUlasan.simpan(current_user, payload, image_file=image_file)
        audit.catat("ulasan_disimpan", "product", ulasan.product_id, f"rating={ulasan.rating}", commit=True)
        return jsonify(message="Ulasan disimpan. Terima kasih!", review=ulasan.to_dict()), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 422
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except PermissionError as exc:
        return jsonify(error=str(exc)), 403
