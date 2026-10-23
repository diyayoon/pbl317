"""Customer: checkout dan pembuatan pesanan. """
from flask import jsonify, render_template, request
from flask_login import current_user, login_required
from app.extensions import db
from app.services.checkout_service import LayananCheckout
from app.services.order_service import LayananPesanan
from app.utils import audit
from app.utils.decorators import role_required
from . import customer_bp



@customer_bp.get("/checkout")
@login_required
@role_required("customer")
def checkout():
    return render_template("customer/checkout.html")


@customer_bp.get("/api/checkout")
@login_required
@role_required("customer")
def api_checkout_data():
    direct_id = request.args.get("direct_product_id", type=int)
    quantity = request.args.get("quantity", default=1, type=int)
    try:
        return jsonify(LayananCheckout(current_user).data_checkout(direct_id, quantity))
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422


@customer_bp.post("/api/orders")
@login_required
@role_required("customer")
def api_create_order():
    payload = request.get_json(silent=True) or {}
    try:
        LayananPesanan.kedaluwarsakan()
        address_id = int(payload.get("address_id"))
        direct_id = int(payload["direct_product_id"]) if payload.get("direct_product_id") else None
        quantity = int(payload.get("quantity", 1))
        order = LayananCheckout(current_user).buat_pesanan(address_id, str(payload.get("payment_method", "")), direct_id, quantity)
        audit.catat("pesanan_dibuat", "order", order.id, f"{order.order_number} total={int(order.total)}", commit=True)
        return jsonify(message="Pesanan berhasil dibuat.", order=order.to_dict()), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc) or "Data checkout tidak valid."), 422
    except LookupError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 404
