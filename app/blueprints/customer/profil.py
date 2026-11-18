from pathlib import Path

from flask import current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.extensions import db
from app.models import Order, User
from app.services.customer_service import LayananPelanggan
from app.services.order_service import LayananPesanan
from app.utils.decorators import role_required
from app.utils.uploads import simpan_gambar_upload
from . import customer_bp



def _hapus_avatar_lama(referensi: str | None) -> None:
    awalan = "/media/avatars/"
    if not isinstance(referensi, str) or not referensi.startswith(awalan):
        return
    nama_file = referensi[len(awalan):]
    if not nama_file or Path(nama_file).name != nama_file:
        return
    folder = Path(current_app.config["AVATAR_UPLOAD_FOLDER"]).resolve()
    target = (folder / nama_file).resolve()
    if folder in target.parents and target.is_file():
        try:
            target.unlink()
        except OSError:
            current_app.logger.warning("Gagal menghapus foto profil lama %s", target.name)



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
    user = db.session.get(User, current_user.id)
    if user is None:
        return jsonify(error="Akun tidak ditemukan."), 404

    multipart = request.mimetype == "multipart/form-data"
    payload = request.form.to_dict() if multipart else (request.get_json(silent=True) or {})
    if not isinstance(payload, dict):
        return jsonify(error="Data profil tidak valid."), 422

    if not multipart and "foto" in payload:
        return jsonify(error="Foto profil harus dikirim sebagai berkas multipart/form-data."), 415

    upload_baru = None
    avatar_path = None
    hapus_foto = str(payload.pop("hapus_foto", "")).strip().lower() in {"1", "true", "yes"}
    avatar_lama = user.avatar_data

    try:
        foto = request.files.get("foto") if multipart else None
        if foto and foto.filename:
            upload_baru = simpan_gambar_upload(
                foto,
                current_app.config["AVATAR_UPLOAD_FOLDER"],
                current_app.config["AVATAR_MAX_BYTES"],
            )
            avatar_path = f"/media/avatars/{upload_baru.name}"

        hasil = LayananPelanggan.update_profile(
            user,
            payload,
            avatar_path=avatar_path,
            remove_avatar=hapus_foto,
        )
    except ValueError as exc:
        db.session.rollback()
        if upload_baru:
            upload_baru.unlink(missing_ok=True)
        return jsonify(error=str(exc)), 422
    except IntegrityError:
        db.session.rollback()
        if upload_baru:
            upload_baru.unlink(missing_ok=True)
        return jsonify(error="Data profil bentrok dengan akun lain."), 409
    except SQLAlchemyError:
        db.session.rollback()
        if upload_baru:
            upload_baru.unlink(missing_ok=True)
        current_app.logger.exception("Gagal menyimpan profil customer %s", current_user.id)
        return jsonify(error="Profil belum dapat disimpan. Silakan coba kembali."), 500

    if avatar_lama and avatar_lama != hasil["foto"]:
        _hapus_avatar_lama(avatar_lama)
    return jsonify(message="Profil disimpan.", profile=hasil)


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
