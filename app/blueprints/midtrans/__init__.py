"""Penerima notifikasi HTTP Midtrans (publik, tanpa login, tanpa CSRF; dilindungi signature)."""
from flask import Blueprint, current_app, jsonify, request
from app.extensions import csrf, db
from app.services.midtrans_service import ErrorMidtrans, LayananMidtrans, aktif, signature_valid

midtrans_bp = Blueprint("midtrans", __name__, url_prefix="/midtrans")


@midtrans_bp.post("/notifikasi")
@csrf.exempt
def notifikasi():
    if not aktif():
        return jsonify(error="nonaktif"), 503
    data = request.get_json(silent=True)
    # Jangan mensyaratkan Content-Length (pengiriman chunked tidak menyertakannya); ukuran dibatasi dari isi sebenarnya.
    if not isinstance(data, dict) or len(request.get_data(cache=True)) > 20000:
        return jsonify(error="payload tidak valid"), 400
    if not signature_valid(data):
        current_app.logger.warning("Notifikasi Midtrans ditolak: signature tidak valid.")
        return jsonify(error="signature tidak valid"), 403
    try:
        # Jangan percaya isi notifikasi mentah: ambil status resmi dari Midtrans lalu terapkan.
        resmi = LayananMidtrans.ambil_status(str(data.get("order_id", "")))
        hasil = LayananMidtrans.terapkan(resmi)
        current_app.logger.info("Notifikasi Midtrans diproses (%s).", hasil)
    except ErrorMidtrans as exc:
        db.session.rollback()
        return jsonify(error=exc.pesan), exc.kode   # 5xx membuat Midtrans mencoba kirim ulang
    return jsonify(ok=True), 200
