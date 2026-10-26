"""Integrasi Midtrans Snap (mode Redirect): buat transaksi, verifikasi notifikasi, sinkron status."""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from flask import current_app, url_for
from sqlalchemy import select
from app.extensions import db
from app.models import Order
from app.services.order_service import LayananPesanan
from app.utils import audit

LUNAS = {"settlement"}          # capture dihitung lunas hanya bila fraud_status == accept
GAGAL_BATAL = {"cancel", "expire"}


class ErrorMidtrans(Exception):
    def __init__(self, pesan: str, kode: int = 502):
        super().__init__(pesan)
        self.pesan, self.kode = pesan, kode


def aktif() -> bool:
    return bool(current_app.config.get("MIDTRANS_SERVER_KEY"))


def _basis() -> tuple[str, str]:
    prod = current_app.config.get("MIDTRANS_IS_PRODUCTION")
    return ("https://app.midtrans.com", "https://api.midtrans.com") if prod else \
           ("https://app.sandbox.midtrans.com", "https://api.sandbox.midtrans.com")


def _http(metode: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    """Satu-satunya titik keluar jaringan (mudah di-mock saat test). Kunci server hanya di header Authorization."""
    kunci = current_app.config["MIDTRANS_SERVER_KEY"]
    header = {"Accept": "application/json", "Content-Type": "application/json",
              "Authorization": "Basic " + base64.b64encode(f"{kunci}:".encode()).decode()}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=header, method=metode)  # noqa: S310 (URL tetap dari konstanta)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        current_app.logger.error("Midtrans tidak terjangkau (%s).", type(exc).__name__)
        raise ErrorMidtrans("Layanan pembayaran sedang tidak dapat dihubungi. Coba lagi sebentar lagi.", 503) from exc


def signature_valid(data: dict) -> bool:
    """SHA512(order_id + status_code + gross_amount + server_key), dibandingkan secara constant-time."""
    kunci = current_app.config.get("MIDTRANS_SERVER_KEY") or ""
    bahan = f"{data.get('order_id', '')}{data.get('status_code', '')}{data.get('gross_amount', '')}{kunci}"
    benar = hashlib.sha512(bahan.encode()).hexdigest()
    return bool(kunci) and hmac.compare_digest(benar, str(data.get("signature_key", "")))


class LayananMidtrans:
    @staticmethod
    def buat_transaksi(order: Order) -> str:
        """Kembalikan URL halaman bayar Midtrans. Dipakai ulang bila transaksi untuk pesanan ini sudah dibuat."""
        if not aktif():
            raise ErrorMidtrans("Pembayaran online belum diaktifkan.", 503)
        if order.payment_method != "Midtrans" or order.status != "Menunggu pembayaran":
            raise ErrorMidtrans("Pesanan ini tidak dapat dibayar lewat Midtrans.", 409)
        payment = order.payment
        if payment is None:
            raise ErrorMidtrans("Data pembayaran tidak ditemukan.", 404)
        if payment.snap_redirect_url:
            return payment.snap_redirect_url
        cfg = current_app.config
        dasar = cfg.get("APP_BASE_URL") or ""
        body = {
            "transaction_details": {"order_id": order.order_number, "gross_amount": int(order.total)},
            "customer_details": {"first_name": order.user.nama[:100], "email": order.user.email},
            "callbacks": {"finish": f"{dasar}{url_for('customer.pesanan')}?midtrans=selesai"},
        }
        ttl = int(cfg.get("ORDER_PAYMENT_TTL_JAM", 24))
        if ttl > 0:
            body["expiry"] = {"unit": "hour", "duration": ttl}
        status, hasil = _http("POST", f"{_basis()[0]}/snap/v1/transactions", body)
        url = str(hasil.get("redirect_url") or "")
        if status not in (200, 201) or not url.startswith("https://"):
            alasan = hasil.get("error_messages") if isinstance(hasil.get("error_messages"), list) else []
            current_app.logger.error("Midtrans menolak pembuatan transaksi (HTTP %s): %s", status, "; ".join(map(str, alasan))[:300])
            raise ErrorMidtrans("Transaksi pembayaran gagal dibuat. Coba lagi atau gunakan metode lain.", 502)
        payment.snap_redirect_url = url[:500]
        audit.catat("midtrans_transaksi_dibuat", "order", order.id, order.order_number)
        db.session.commit()
        return url

    @staticmethod
    def ambil_status(ref: str) -> dict:
        status, hasil = _http("GET", f"{_basis()[1]}/v2/{ref}/status")
        if status == 404 or str(hasil.get("status_code")) == "404":
            raise ErrorMidtrans("Transaksi belum ada di Midtrans.", 404)
        if status != 200:
            raise ErrorMidtrans("Gagal membaca status dari Midtrans.", 502)
        return hasil

    @staticmethod
    def terapkan(data: dict) -> str:
        """Terapkan status Midtrans yang SUDAH terverifikasi. Idempoten, aman terhadap notifikasi tidak berurutan."""
        ref = str(data.get("order_id") or "")
        # Cari lewat order_number (selalu ada): tetap benar walau penyimpanan URL bayar pernah gagal.
        order = db.session.scalar(select(Order).where(Order.order_number == ref, Order.payment_method == "Midtrans").with_for_update())
        payment = order.payment if order else None
        if payment is None:
            raise ErrorMidtrans("Pesanan tidak dikenal.", 404)
        try:
            jumlah = Decimal(str(data.get("gross_amount")))
        except InvalidOperation as exc:
            raise ErrorMidtrans("Jumlah pembayaran tidak valid.", 400) from exc
        if jumlah != Decimal(order.total):
            audit.catat("midtrans_jumlah_tidak_cocok", "order", order.id, order.order_number, commit=True)
            raise ErrorMidtrans("Jumlah pembayaran tidak cocok dengan pesanan.", 400)
        ts, fraud = str(data.get("transaction_status") or ""), str(data.get("fraud_status") or "")
        if payment.status == "Disetujui":   # sudah lunas: notifikasi susulan (pending/refund) tidak menurunkan status
            return "lunas"
        payment.gateway_status = ts[:30]
        payment.gateway_payment_type = str(data.get("payment_type") or "")[:40] or None
        payment.gateway_transaction_id = str(data.get("transaction_id") or "")[:64] or None
        hasil = "menunggu"
        if ts in LUNAS or (ts == "capture" and fraud == "accept"):
            if order.status == "Menunggu pembayaran":
                payment.status, payment.paid_at = "Disetujui", datetime.now(timezone.utc)
                payment.review_note = f"Lunas via Midtrans ({payment.gateway_payment_type or 'online'})."
                order.status = "Diproses"
                audit.catat("midtrans_lunas", "order", order.id, order.order_number)
                hasil = "lunas"
            else:   # dibayar setelah pesanan dibatalkan/kedaluwarsa: stok sudah dilepas, butuh keputusan admin
                payment.paid_at = datetime.now(timezone.utc)
                payment.review_note = "Dibayar setelah pesanan dibatalkan; perlu penanganan admin (refund/aktifkan ulang)."
                audit.catat("midtrans_bayar_setelah_batal", "order", order.id, order.order_number)
                hasil = "perlu_penanganan"
        elif ts in GAGAL_BATAL and order.status == "Menunggu pembayaran":
            LayananPesanan.kembalikan_stok(order)
            order.status = "Dibatalkan"
            payment.status = "Kedaluwarsa" if ts == "expire" else "Dibatalkan"
            payment.review_note = f"Transaksi Midtrans {ts}."
            audit.catat(f"midtrans_{ts}", "order", order.id, order.order_number)
            hasil = "dibatalkan"
        db.session.commit()
        return hasil

    @staticmethod
    def batalkan_di_midtrans(order: Order) -> None:
        """Best effort: matikan transaksi di Midtrans agar tautan bayar tidak terpakai. Kegagalan hanya dicatat."""
        try:
            _http("POST", f"{_basis()[1]}/v2/{order.order_number}/cancel")
        except ErrorMidtrans:
            current_app.logger.warning("Pembatalan di Midtrans gagal; pembayaran susulan akan ditandai untuk admin.")

    @classmethod
    def sinkron(cls, order: Order) -> str:
        """Tanya status resmi ke Midtrans (server-ke-server) lalu terapkan. Tidak butuh webhook publik."""
        if not aktif():
            raise ErrorMidtrans("Pembayaran online belum diaktifkan.", 503)
        if order.payment_method != "Midtrans":
            raise ErrorMidtrans("Pesanan ini bukan pembayaran Midtrans.", 409)
        try:
            return cls.terapkan(cls.ambil_status(order.order_number))
        except ErrorMidtrans as exc:
            if exc.kode == 404:   # transaksi belum pernah dibuka di Midtrans
                return "belum_dibuat"
            raise
