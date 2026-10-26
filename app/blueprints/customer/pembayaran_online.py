"""Customer: bayar pesanan lewat Midtrans (Snap Redirect) dan sinkron status sesudah kembali."""
from flask import jsonify
from flask_login import current_user, login_required
from app.extensions import db
from app.models import Order
from app.services.midtrans_service import ErrorMidtrans, LayananMidtrans
from app.utils.decorators import role_required, terverifikasi_required
from . import customer_bp


def _order_milik_sendiri(order_id: int) -> Order | None:
    return db.session.scalar(db.select(Order).where(Order.id == order_id, Order.user_id == current_user.id))


@customer_bp.post("/api/orders/<int:order_id>/midtrans")
@login_required
@role_required("customer")
@terverifikasi_required
def api_bayar_midtrans(order_id: int):
    order = _order_milik_sendiri(order_id)
    if order is None:
        return jsonify(error="Pesanan tidak ditemukan."), 404
    try:
        return jsonify(redirectUrl=LayananMidtrans.buat_transaksi(order))
    except ErrorMidtrans as exc:
        db.session.rollback()
        return jsonify(error=exc.pesan), exc.kode


@customer_bp.post("/api/orders/<int:order_id>/midtrans/sinkron")
@login_required
@role_required("customer")
def api_sinkron_midtrans(order_id: int):
    order = _order_milik_sendiri(order_id)
    if order is None:
        return jsonify(error="Pesanan tidak ditemukan."), 404
    try:
        hasil = LayananMidtrans.sinkron(order)
    except ErrorMidtrans as exc:
        db.session.rollback()
        return jsonify(error=exc.pesan), exc.kode
    db.session.refresh(order)
    return jsonify(hasil=hasil, status=order.status, statusPembayaran=order.payment.status if order.payment else "")
