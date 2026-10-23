"""Customer: keranjang belanja. (pemilik: Fiony)"""
from flask import jsonify, render_template, request
from flask_login import current_user, login_required
from app.extensions import db
from app.services.customer_service import LayananPelanggan
from app.utils.decorators import role_required
from . import customer_bp



@customer_bp.get("/keranjang")
@login_required
@role_required("customer")
def keranjang():
    return render_template("customer/cart.html")


@customer_bp.get("/api/cart")
@login_required
@role_required("customer")
def api_cart():
    return jsonify(items=LayananPelanggan.daftar_keranjang(current_user))


@customer_bp.post("/api/cart")
@login_required
@role_required("customer")
def api_add_cart():
    payload = request.get_json(silent=True) or {}
    try:
        item = LayananPelanggan.tambah_keranjang(current_user, int(payload.get("product_id")), int(payload.get("quantity", 1)))
        return jsonify(message="Produk ditambahkan ke keranjang.", item=item, items=LayananPelanggan.daftar_keranjang(current_user)), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc) or "Data produk tidak valid."), 422
    except LookupError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 404


@customer_bp.put("/api/cart/<int:product_id>")
@login_required
@role_required("customer")
def api_update_cart_item(product_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        item = LayananPelanggan.ubah_keranjang(
            current_user, product_id,
            quantity=int(payload["quantity"]) if "quantity" in payload else None,
            selected=bool(payload["selected"]) if "selected" in payload else None,
        )
        return jsonify(message="Keranjang diperbarui.", item=item, items=LayananPelanggan.daftar_keranjang(current_user))
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc) or "Data tidak valid."), 422
    except LookupError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 404


@customer_bp.put("/api/cart/pilih-semua")
@login_required
@role_required("customer")
def api_select_all_cart():
    payload = request.get_json(silent=True) or {}
    return jsonify(items=LayananPelanggan.pilih_semua(current_user, bool(payload.get("selected"))))


@customer_bp.delete("/api/cart/<int:product_id>")
@login_required
@role_required("customer")
def api_delete_cart_item(product_id: int):
    LayananPelanggan.hapus_keranjang(current_user, product_id=product_id)
    return jsonify(message="Produk dihapus dari keranjang.", items=LayananPelanggan.daftar_keranjang(current_user))
