"""Autentikasi pengguna (PostgreSQL). Semua registrasi publik otomatis menjadi customer."""
from __future__ import annotations

from urllib.parse import urlsplit

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User
from app.utils import audit, ratelimit
from app.utils.network import client_ip
from app.utils.validasi import ValidasiRegistrasi
from . import auth_bp

# Hash tiruan agar waktu respons sama baik email ada maupun tidak (anti user-enumeration).
_HASH_TIRUAN = generate_password_hash("password-tiruan-untuk-menyamakan-waktu")


def _next_aman(target: str) -> str | None:
    """Hanya path internal; menolak skema, host, //, dan backslash (open redirect)."""
    if not target or "\\" in target or any(ord(c) < 32 for c in target):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


def _terlalu_banyak(email: str, ip: str) -> bool:
    cfg, w = current_app.config, current_app.config["LOGIN_WINDOW_MENIT"]
    return (
        ratelimit.terblokir("login_email", email, cfg["LOGIN_MAX_PER_EMAIL"], w)
        or ratelimit.terblokir("login_ip", ip, cfg["LOGIN_MAX_PER_IP"], w)
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.halaman_awal()))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")[:200]
        ip = client_ip()

        if _terlalu_banyak(email, ip):
            audit.catat("login_diblokir", "user", email, "melewati batas percobaan", email=email, commit=True)
            flash(f"Terlalu banyak percobaan masuk. Coba lagi dalam {current_app.config['LOGIN_WINDOW_MENIT']} menit.", "danger")
            return render_template("auth/login.html"), 429

        user = User.query.filter_by(email=email).first() if email else None
        sah = check_password_hash(user.password_hash if user else _HASH_TIRUAN, password) and user is not None and user.is_active and len(password) <= 128
        if sah:
            ratelimit.bersihkan("login_email", email)
            session.clear()
            login_user(user, remember=request.form.get("remember") == "on")
            session.permanent = True
            audit.catat("login_berhasil", "user", user.id, actor=user, commit=True)
            return redirect(_next_aman(request.args.get("next", "")) or url_for(user.halaman_awal()))

        ratelimit.catat("login_email", email)
        ratelimit.catat("login_ip", ip)
        audit.catat("login_gagal", "user", email or "-", "kredensial tidak cocok", email=email, commit=True)
        flash("Email atau kata sandi tidak sesuai.", "danger")
        return render_template("auth/login.html"), 401

    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        audit.catat("logout", "user", current_user.id, commit=True)
    logout_user()
    session.clear()
    return redirect(url_for("main.beranda"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registrasi publik: role selalu customer; admin hanya dibuat lewat `flask create-admin`."""
    nilai: dict = {}
    galat: dict = {}
    if request.method == "POST":
        ip = client_ip()
        cfg = current_app.config
        if ratelimit.terblokir("register_ip", ip, cfg["REGISTER_MAX_PER_IP"], cfg["REGISTER_WINDOW_MENIT"]):
            flash("Terlalu banyak pembuatan akun dari jaringan ini. Coba lagi nanti.", "danger")
            return render_template("auth/register.html", nilai={}, galat={}), 429
        ratelimit.catat("register_ip", ip)

        nilai, galat = ValidasiRegistrasi(request.form).periksa()
        email = nilai.get("email", "")
        if not galat and User.query.filter_by(email=email).first():
            galat["email"] = "Email ini sudah terdaftar. Silakan masuk atau gunakan email lain."
        if galat:
            return render_template("auth/register.html", nilai=nilai, galat=galat), 422
        user = User(email=email, nama=nilai["nama"], role="customer", telepon=nilai["telepon"], alamat_registrasi=nilai["alamat"])
        user.set_password(request.form.get("password", ""))
        try:
            db.session.add(user)
            db.session.flush()
            audit.catat("registrasi", "user", user.id, actor=user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            galat["email"] = "Email ini sudah terdaftar. Silakan masuk atau gunakan email lain."
            return render_template("auth/register.html", nilai=nilai, galat=galat), 422
        flash("Akun berhasil dibuat. Silakan masuk.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", nilai=nilai, galat=galat)
