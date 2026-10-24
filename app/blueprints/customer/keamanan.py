"""Customer: ganti kata sandi. (pemilik: Arga)"""
from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user
from app.extensions import db
from app.models import User
from app.services.account_service import LayananAkun
from app.services.sesi_service import LayananSesi
from app.utils.decorators import role_required
from . import customer_bp



@customer_bp.route("/keamanan", methods=["GET", "POST"])
@login_required
@role_required("customer")
def keamanan():
    if request.method == "POST":
        user = db.session.get(User, current_user.id)
        try:
            LayananAkun.ganti_password(
                user, request.form.get("password_lama", ""), request.form.get("password_baru", ""),
                request.form.get("konfirmasi_password", ""),
            )
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            LayananSesi.cabut_semua(user.id)
            session.clear()
            login_user(user)
            LayananSesi.mulai(user)  # sesi ini tetap hidup; sesi perangkat lain tercabut
            flash("Kata sandi berhasil diperbarui. Sesi di perangkat lain telah dikeluarkan.", "success")
            return redirect(url_for("customer.keamanan"))
    return render_template("customer/security.html")
