"""Penegakan timeout inaktivitas di setiap request (bukan timer JavaScript)."""
from flask import flash, g, request, session
from flask_login import current_user
from .services.sesi_service import LayananSesi

PESAN = {
    "tidak_aktif": "Sesi berakhir karena tidak ada aktivitas. Silakan masuk lagi.",
    "terlalu_lama": "Sesi berakhir karena sudah terlalu lama. Silakan masuk lagi.",
}


def _abaikan() -> bool:
    """Request yang tidak diperiksa dan tidak dianggap aktivitas (aset, health check)."""
    return request.endpoint in (None, "static", "health", "media_produk") or request.path.startswith("/static/")


def _aktivitas_user() -> bool:
    """Polling/heartbeat/request latar belakang menandai dirinya dengan header ini dan tidak memperpanjang sesi."""
    return request.method != "HEAD" and request.headers.get("X-Background-Request") != "1"


def init_sesi(app):
    @app.before_request
    def jaga_sesi():
        if _abaikan() or "_user_id" not in session:
            return None
        if current_user.is_authenticated:  # user_loader sudah memvalidasi record sesi
            if _aktivitas_user():
                LayananSesi.sentuh()
            return None
        alasan = g.get("sesi_alasan")
        session.clear()
        if alasan in PESAN and "/api/" not in request.path:
            flash(PESAN[alasan], "warning")
        return None
