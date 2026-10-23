"""Customer: dashboard, profil, alamat. (pemilik: Fiony)"""
from flask import jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Order, User
from app.services.customer_service import LayananPelanggan
from app.services.order_service import LayananPesanan
from app.utils.decorators import role_required
from . import customer_bp



@customer_bp.get("/akun")
@login_required
@role_required("customer")
def dashboard():
    return render_template("customer/dashboard.html")


@customer_bp.get("/profil")
@login_required
@role_required("customer")
def profil():
    return render_template("customer/profile.html")


@customer_bp.get("/api/profile")
@login_required
@role_required("customer")
def api_profile():
    return jsonify({
        "nama": current_user.nama, "email": current_user.email,
        "telepon": current_user.telepon, "foto": current_user.avatar_data,
        "alamat_registrasi": current_user.alamat_registrasi or "",
    })


@customer_bp.put("/api/profile")
@login_required
@role_required("customer")
def api_update_profile():
    try:
        payload = LayananPelanggan.update_profile(db.session.get(User, current_user.id), request.get_json(silent=True) or {})
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Data profil bentrok dengan akun lain."), 409
    return jsonify(message="Profil disimpan.", profile=payload)


@customer_bp.get("/api/addresses")
@login_required
@role_required("customer")
def api_addresses():
    return jsonify(LayananPelanggan.daftar_alamat(current_user))


@customer_bp.put("/api/addresses")
@login_required
@role_required("customer")
def api_replace_addresses():
    try:
        data = LayananPelanggan.simpan_daftar_alamat(current_user, request.get_json(silent=True) or {})
        return jsonify(message="Alamat berhasil disimpan.", **data)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@customer_bp.get("/api/dashboard-summary")
@login_required
@role_required("customer")
def api_dashboard_summary():
    LayananPesanan.kedaluwarsakan()
    base = Order.query.filter_by(user_id=current_user.id)
    orders = base.order_by(Order.created_at.desc()).limit(3).all()
    cart = LayananPelanggan.daftar_keranjang(current_user)
    addresses = LayananPelanggan.daftar_alamat(current_user)["daftar"]
    return jsonify(orders=[o.to_dict() for o in orders], order_count=base.count(), cart=cart, addresses=addresses)
