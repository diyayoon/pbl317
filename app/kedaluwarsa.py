"""Kedaluwarsa pesanan berkala di dalam aplikasi (tanpa cron): stok pesanan yang tidak dibayar kembali sendiri."""
import time
from flask import request
from .extensions import db
from .services.order_service import LayananPesanan

_terakhir = None   # None = belum pernah dijalankan (jangan bergantung pada nilai time.monotonic)


def init_kedaluwarsa(app):
    @app.before_request
    def kedaluwarsakan_berkala():
        global _terakhir
        interval = int(app.config.get("ORDER_EXPIRE_INTERVAL_DETIK", 60))
        if interval <= 0 or request.endpoint in (None, "static", "health", "media_produk"):
            return None
        sekarang = time.monotonic()
        if _terakhir is not None and sekarang - _terakhir < interval:
            return None
        _terakhir = sekarang
        try:
            LayananPesanan.kedaluwarsakan()   # idempoten dan aman paralel (FOR UPDATE SKIP LOCKED)
        except Exception:  # noqa: BLE001 - kegagalan housekeeping tidak boleh merusak request user
            db.session.rollback()
            app.logger.exception("Kedaluwarsa pesanan berkala gagal.")
        return None
