"""Penerima notifikasi HTTP Midtrans (publik, tanpa login, tanpa CSRF; dilindungi signature)."""
from flask import Blueprint, current_app, jsonify, request
from app.extensions import csrf, db
from app.services.midtrans_service import ErrorMidtrans, LayananMidtrans, aktif, signature_valid
from app.models import Order
from app.utils import audit
from app.utils.network import client_ip

midtrans_bp = Blueprint("midtrans", __name__, url_prefix="/midtrans")


@midtrans_bp.post("/notifikasi")
@csrf.exempt
def notifikasi():
    if not aktif():
        return jsonify(error="nonaktif"), 503
    data = request.get_json(silent=True)
    # Jangan mensyaratkan Content-Length (pengiriman chunked tidak menyertakannya); ukuran dibatasi dari isi sebenarnya.
    if not isinstance(data, dict) or len(request.get_data(cache=True)) > 20000:
        audit.catat(
            "midtrans_payload_invalid", "notification", "-", "Payload notifikasi kosong, bukan objek JSON, atau melewati batas ukuran.",
            actor_role="gateway", outcome="rejected", severity="medium", commit=True,
        )
        return jsonify(error="payload tidak valid"), 400
    if not signature_valid(data):
        # Jangan pernah mencatat signature mentah atau seluruh payload callback.
        audit.catat(
            "midtrans_signature_invalid", "order", str(data.get("order_id") or "-")[:60],
            "Signature notifikasi Midtrans tidak valid.", actor_role="gateway", outcome="rejected", severity="high",
            context={"status_code": str(data.get("status_code") or "")[:8]}, commit=True,
        )
        current_app.logger.warning("Notifikasi Midtrans ditolak: signature tidak valid.")
        return jsonify(error="signature tidak valid"), 403
    try:
        # Jangan percaya isi notifikasi mentah: ambil status resmi dari Midtrans lalu terapkan.
        resmi = LayananMidtrans.ambil_status(str(data.get("order_id", "")))
        hasil = LayananMidtrans.terapkan(resmi)
        current_app.logger.info("Notifikasi Midtrans diproses (%s).", hasil)
    except ErrorMidtrans as exc:
        db.session.rollback()
        if exc.kode == 404:
            # Jika transaksi tidak ditemukan oleh Midtrans dan order juga tidak ada secara lokal,
            # simpan anomali bertanda tangan valid tanpa mencatat seluruh payload callback.
            ref = str(data.get("order_id") or "")[:60]
            order_lokal = Order.query.filter_by(order_number=ref, payment_method="Midtrans").first() if ref else None
            if order_lokal is None:
                audit.catat(
                    "midtrans_order_not_found", "order", ref or "-",
                    "Callback bertanda tangan valid merujuk transaksi yang tidak ditemukan di Midtrans maupun database lokal.",
                    actor_role="gateway", outcome="rejected", severity="high", commit=True,
                )
        return jsonify(error=exc.pesan), exc.kode   # 5xx membuat Midtrans mencoba kirim ulang
    return jsonify(ok=True), 200
