"""Penerima notifikasi HTTP Midtrans (publik, tanpa login, tanpa CSRF; dilindungi signature)."""

from flask import Blueprint, current_app, jsonify, request

from app.extensions import csrf, db
from app.services.midtrans_service import (
    ErrorMidtrans,
    LayananMidtrans,
    aktif,
    signature_valid,
)
from app.utils import audit


midtrans_bp = Blueprint("midtrans", __name__, url_prefix="/midtrans")


@midtrans_bp.post("/notifikasi")
@csrf.exempt
def notifikasi():
    """Menerima dan memverifikasi notifikasi pembayaran dari Midtrans."""

    # Pastikan integrasi Midtrans sudah dikonfigurasi.
    if not aktif():
        return jsonify(error="nonaktif"), 503

    data = request.get_json(silent=True)

    # Validasi payload dan batasi ukuran request maksimal 20 KB.
    if not isinstance(data, dict) or len(request.get_data(cache=True)) > 20000:
        return jsonify(error="payload tidak valid"), 400

    # Verifikasi signature sebelum memproses notifikasi.
    if not signature_valid(data):
        audit.catat(
            "midtrans_signature_invalid",
            "payment",
            str(data.get("order_id") or "-")[:80],
            "Notifikasi Midtrans ditolak karena signature tidak valid.",
            actor_role="gateway",
            context={"attempted_action": "midtrans_notification"},
            commit=True,
        )

        current_app.logger.warning(
            "Notifikasi Midtrans ditolak: signature tidak valid."
        )

        return jsonify(error="signature tidak valid"), 403

    try:
        # Jangan mempercayai status transaksi dari payload mentah.
        # Ambil status resmi melalui API Midtrans sebelum menerapkannya.
        resmi = LayananMidtrans.ambil_status(
            str(data.get("order_id", ""))
        )

        hasil = LayananMidtrans.terapkan(resmi)

        current_app.logger.info(
            "Notifikasi Midtrans berhasil diproses (%s).",
            hasil,
        )

    except ErrorMidtrans as exc:
        db.session.rollback()

        # Error 5xx memungkinkan Midtrans mencoba mengirim notifikasi ulang.
        return jsonify(error=exc.pesan), exc.kode

    return jsonify(ok=True), 200