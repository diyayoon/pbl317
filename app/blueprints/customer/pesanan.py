"""Customer: riwayat pesanan, bukti bayar, ulasan. (pemilik: Intan)"""
from flask import current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from app.models import Order
from app.services.order_service import LayananPesanan
from app.services.payment_service import LayananPembayaran
from app.services.review_service import LayananUlasan
from app.utils import audit
from app.utils.decorators import role_required
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
        for item in data["items"]:
            item["bisaUlas"] = order.status == "Selesai" and item["id"] is not None
            item["ulasanSaya"] = ulasan.get(item["id"])
        hasil.append(data)
    return jsonify(hasil)


@customer_bp.post("/api/orders/<int:order_id>/bukti")
@login_required
@role_required("customer")
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
def api_save_review():
    try:
        ulasan = LayananUlasan.simpan(current_user, request.get_json(silent=True))
        audit.catat("ulasan_disimpan", "product", ulasan.product_id, f"rating={ulasan.rating}", commit=True)
        return jsonify(message="Ulasan disimpan. Terima kasih!", review=ulasan.to_dict()), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 422
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except PermissionError as exc:
        return jsonify(error=str(exc)), 403
