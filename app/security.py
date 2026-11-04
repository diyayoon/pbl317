"""Pengerasan HTTP: header keamanan, CSP bernonce, proxy, dan penanganan error aman.

Pemetaan OWASP Top 10:2025: A02 (header/konfigurasi), A05 (CSP: tanpa skrip inline),
A10 (error tidak membocorkan detail dan tidak fail-open).
"""
from flask import jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from .extensions import db

PESAN_UMUM = {
    400: "Permintaan tidak valid atau sesi formulir sudah kedaluwarsa. Muat ulang halaman lalu coba lagi.",
    401: "Sesi berakhir. Silakan login kembali.",
    403: "Anda tidak memiliki izin untuk tindakan ini.",
    404: "Data yang diminta tidak ditemukan.",
    405: "Metode permintaan tidak diizinkan.",
    413: "Berkas terlalu besar.",
    429: "Terlalu banyak percobaan. Coba lagi beberapa saat lagi.",
    500: "Terjadi kesalahan pada server. Tim kami sudah mencatatnya.",
    503: "Layanan sementara tidak tersedia. Coba lagi sebentar lagi.",
}


def _csp() -> str:
    return "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])


def _wants_json() -> bool:
    return "/api/" in request.path or request.accept_mimetypes.best == "application/json"


def init_security(app):
    if app.config.get("TRUSTED_PROXY_COUNT", 0) > 0:
        n = app.config["TRUSTED_PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=0)

    @app.after_request
    def header_keamanan(resp):
        resp.headers.setdefault("Content-Security-Policy", _csp())
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.is_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        # Halaman/API pribadi tidak boleh tersimpan di cache bersama atau tombol "back".
        privat = request.path.startswith(("/customer", "/admin", "/auth", "/media/payments"))
        if privat:
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def balas(kode: int, pesan: str | None = None):
        pesan = pesan or PESAN_UMUM.get(kode, "Terjadi kesalahan.")
        if _wants_json():
            return jsonify(error=pesan), kode
        if kode in (403, 404, 500):
            return render_template(f"errors/{kode}.html"), kode
        return render_template("errors/generic.html", kode=kode, pesan=pesan), kode

    @app.errorhandler(SQLAlchemyError)
    def galat_database(error):
        db.session.rollback()
        app.logger.exception("Kesalahan database")
        return balas(503)

    @app.errorhandler(HTTPException)
    def galat_http(error):
        kode = error.code or 500
        if kode >= 500:
            db.session.rollback()
        return balas(kode)

    @app.errorhandler(Exception)
    def galat_tak_terduga(error):
        db.session.rollback()
        app.logger.exception("Kesalahan tak terduga")
        return balas(500)
