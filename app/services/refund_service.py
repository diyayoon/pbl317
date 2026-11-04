"""Alur permintaan refund Midtrans: customer mengajukan, admin meninjau, gateway mengonfirmasi."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.extensions import db
from app.models import Order, RefundRequest
from app.services import midtrans_service
from app.services.midtrans_service import ErrorMidtrans
from app.services.order_service import LayananPesanan
from app.utils import audit

# Refund Midtrans hanya didukung untuk metode pembayaran tertentu.
METODE_REFUND = {"credit_card", "gopay", "shopeepay", "dana", "ovo", "qris", "kredivo", "akulaku"}
STATUS_AKTIF = {"Menunggu persetujuan", "Diproses", "Gagal"}


class ErrorRefund(Exception):
    def __init__(self, pesan: str, kode: int = 422):
        super().__init__(pesan)
        self.pesan, self.kode = pesan, kode


class LayananRefund:
    @staticmethod
    def ajukan(order_id: int, customer, alasan: str) -> RefundRequest:
        alasan = " ".join((alasan or "").split())[:500]
        if len(alasan) < 10:
            raise ErrorRefund("Alasan refund wajib diisi minimal 10 karakter.")
        if not midtrans_service.aktif():
            raise ErrorRefund("Layanan Midtrans belum dikonfigurasi.", 503)

        order = db.session.scalar(
            select(Order).where(Order.id == order_id, Order.user_id == customer.id).with_for_update()
        )
        if order is None:
            raise ErrorRefund("Pesanan tidak ditemukan.", 404)
        if order.status != "Diproses":
            raise ErrorRefund("Refund hanya dapat diajukan sebelum pesanan dikirim.", 409)
        if order.payment_method != "Midtrans" or order.payment is None or order.payment.status != "Disetujui":
            raise ErrorRefund("Hanya pesanan Midtrans yang sudah dibayar yang dapat diajukan refund.", 409)

        aktif = db.session.scalar(
            select(RefundRequest.id).where(
                RefundRequest.order_id == order.id,
                RefundRequest.status.in_(STATUS_AKTIF),
            ).limit(1)
        )
        if aktif:
            raise ErrorRefund("Masih ada permintaan refund yang sedang ditangani.", 409)

        # Validasi status langsung ke Midtrans, bukan hanya mengandalkan status dari browser.
        gateway = midtrans_service.LayananMidtrans.ambil_status(order.order_number)
        try:
            jumlah = Decimal(str(gateway.get("gross_amount")))
        except (InvalidOperation, TypeError) as exc:
            raise ErrorRefund("Jumlah transaksi dari Midtrans tidak valid.", 502) from exc
        if jumlah != Decimal(order.total):
            raise ErrorRefund("Jumlah transaksi Midtrans tidak cocok dengan pesanan.", 409)
        status_gateway = str(gateway.get("transaction_status") or "")
        tipe = str(gateway.get("payment_type") or "")
        fraud = str(gateway.get("fraud_status") or "")
        if status_gateway not in {"settlement", "capture"} or (status_gateway == "capture" and fraud != "accept"):
            raise ErrorRefund("Transaksi belum berstatus lunas di Midtrans atau tidak dapat direfund.", 409)
        if status_gateway == "settlement" and tipe not in METODE_REFUND:
            raise ErrorRefund(
                f"Metode pembayaran {tipe or 'ini'} tidak didukung endpoint refund Midtrans. Hubungi admin untuk penanganan manual.",
                409,
            )
        if status_gateway == "capture" and tipe != "credit_card":
            raise ErrorRefund("Pembatalan transaksi berstatus capture hanya tersedia untuk kartu kredit.", 409)

        order.payment.gateway_status = status_gateway[:30]
        order.payment.gateway_payment_type = tipe[:40] or None
        order.payment.gateway_transaction_id = str(gateway.get("transaction_id") or "")[:64] or order.payment.gateway_transaction_id
        refund = RefundRequest(
            order_id=order.id,
            user_id=customer.id,
            reason=alasan,
            amount=order.total,
            status="Menunggu persetujuan",
            refund_key=f"RF-{order.order_number}-{secrets.token_hex(4)}",
            gateway_status=status_gateway,
            gateway_payment_type=tipe[:40] or None,
        )
        db.session.add(refund)
        db.session.flush()
        audit.catat("refund_diajukan", "refund", refund.id, f"{order.order_number}; jumlah={int(refund.amount)}", actor=customer)
        db.session.commit()
        return refund

    @staticmethod
    def daftar_admin() -> list[dict]:
        rows = db.session.scalars(
            select(RefundRequest).order_by(RefundRequest.requested_at.desc(), RefundRequest.id.desc())
        ).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def _kirim_ke_midtrans(refund: RefundRequest) -> dict:
        order = refund.order
        if order is None or order.payment is None:
            raise ErrorMidtrans("Data pesanan atau pembayaran tidak ditemukan.", 404)
        tipe = refund.gateway_payment_type or order.payment.gateway_payment_type or ""
        status_gateway = refund.gateway_status or order.payment.gateway_status or ""
        body = {"refund_key": refund.refund_key, "amount": int(refund.amount), "reason": refund.reason[:255]}
        if status_gateway == "settlement":
            if tipe not in METODE_REFUND:
                raise ErrorMidtrans("Metode pembayaran ini tidak didukung refund Midtrans.", 409)
            endpoint = f"{midtrans_service._basis()[1]}/v2/{order.order_number}/refund"
        elif status_gateway == "capture" and tipe == "credit_card":
            # Dokumentasi Midtrans: status Capture/Authorize yang belum Settlement menggunakan Cancel API.
            endpoint = f"{midtrans_service._basis()[1]}/v2/{order.order_number}/cancel"
            body = None
        else:
            raise ErrorMidtrans("Status transaksi tidak memenuhi syarat refund atau cancel Midtrans.", 409)
        code, result = midtrans_service._http("POST", endpoint, body)
        if code not in (200, 201, 202) or str(result.get("status_code", "200"))[0] != "2":
            message = str(result.get("status_message") or result.get("error_messages") or "Permintaan ditolak Midtrans")[:250]
            raise ErrorMidtrans(message, 502 if code >= 500 else 409)
        return result

    @classmethod
    def tinjau(cls, refund_id: int, admin, aksi: str, catatan: str = "") -> RefundRequest:
        refund = db.session.scalar(select(RefundRequest).where(RefundRequest.id == refund_id).with_for_update())
        if refund is None:
            raise ErrorRefund("Permintaan refund tidak ditemukan.", 404)
        catatan = " ".join((catatan or "").split())[:500]
        if aksi == "tolak":
            if refund.status != "Menunggu persetujuan":
                raise ErrorRefund("Hanya permintaan yang menunggu persetujuan yang dapat ditolak.", 409)
            if len(catatan) < 5:
                raise ErrorRefund("Alasan penolakan minimal 5 karakter.")
            refund.status = "Ditolak"
            refund.admin_note = catatan
            refund.reviewed_by = admin.id
            refund.reviewed_at = datetime.now(timezone.utc)
            audit.catat("refund_ditolak", "refund", refund.id, catatan, actor=admin)
            db.session.commit()
            return refund

        if aksi != "setujui":
            raise ErrorRefund("Aksi refund tidak dikenal.")
        if refund.status not in {"Menunggu persetujuan", "Gagal"}:
            raise ErrorRefund("Permintaan ini sudah dikirim ke gateway atau sudah selesai.", 409)
        if refund.order.status != "Diproses" or refund.order.payment.status != "Disetujui":
            raise ErrorRefund("Status pesanan/pembayaran sudah berubah; refund tidak dapat diproses.", 409)

        # Commit status sebelum jaringan dipanggil agar request timeout bisa ditelusuri.
        refund.status = "Diproses"
        refund.reviewed_by = admin.id
        refund.reviewed_at = datetime.now(timezone.utc)
        refund.admin_note = catatan or "Disetujui admin; menunggu konfirmasi Midtrans."
        db.session.commit()
        try:
            result = cls._kirim_ke_midtrans(refund)
        except ErrorMidtrans as exc:
            refund.status = "Gagal"
            refund.admin_note = f"Permintaan gateway belum berhasil dipastikan: {exc.pesan}"[:500]
            audit.catat("refund_gateway_gagal", "refund", refund.id, type(exc).__name__, actor=admin)
            db.session.commit()
            raise ErrorRefund(refund.admin_note, exc.kode) from exc

        refund.gateway_status = str(result.get("transaction_status") or result.get("status_message") or "request_accepted")[:40]
        refund.gateway_refund_id = str(result.get("refund_chargeback_id") or result.get("transaction_id") or "")[:100] or None
        refund.admin_note = catatan or "Permintaan dikirim ke Midtrans; menunggu konfirmasi akhir gateway."
        audit.catat("refund_dikirim_ke_gateway", "refund", refund.id, refund.gateway_status, actor=admin)
        db.session.commit()
        return refund

    @classmethod
    def sinkronkan(cls, refund_id: int, admin=None) -> RefundRequest:
        refund = db.session.scalar(select(RefundRequest).where(RefundRequest.id == refund_id).with_for_update())
        if refund is None:
            raise ErrorRefund("Permintaan refund tidak ditemukan.", 404)
        if refund.status == "Berhasil":
            return refund
        if refund.status != "Diproses":
            raise ErrorRefund("Hanya refund yang sedang diproses dapat disinkronkan.", 409)
        data = midtrans_service.LayananMidtrans.ambil_status(refund.order.order_number)
        gateway_status = str(data.get("transaction_status") or "")
        refunds = data.get("refunds") if isinstance(data.get("refunds"), list) else []
        detail = next((item for item in refunds if str(item.get("refund_key") or "") == refund.refund_key), None)
        try:
            nominal_refund = Decimal(str(detail.get("refund_amount"))) if detail else Decimal("0")
        except (InvalidOperation, TypeError):
            nominal_refund = Decimal("0")
        # Hanya tandai selesai bila gateway mengonfirmasi refund penuh yang diminta.
        terkonfirmasi = bool(
            detail and detail.get("bank_confirmed_at")
            and nominal_refund == Decimal(refund.amount)
        )
        dibatalkan = gateway_status == "cancel"
        if (gateway_status in {"refund", "partial_refund"} and terkonfirmasi) or dibatalkan:
            order = refund.order
            payment = order.payment
            # Kembalikan stok satu kali, hanya setelah gateway mengonfirmasi akhir refund/cancel.
            LayananPesanan.kembalikan_stok(order)
            if dibatalkan:
                order.status = "Dibatalkan"
                payment.status = "Dibatalkan"
                payment.review_note = "Transaksi Midtrans dibatalkan setelah persetujuan refund admin."
            else:
                order.status = "Direfund"
                payment.status = "Direfund"
                payment.review_note = "Refund dikonfirmasi Midtrans."
            refund.status = "Berhasil"
            refund.gateway_status = gateway_status
            refund.completed_at = datetime.now(timezone.utc)
            refund.admin_note = "Refund/cancel telah dikonfirmasi oleh Midtrans."
            audit.catat("refund_terkonfirmasi", "refund", refund.id, f"{order.order_number}: {gateway_status}", actor=admin)
        else:
            refund.gateway_status = gateway_status[:40]
            refund.admin_note = "Midtrans belum memberikan konfirmasi akhir. Sinkronkan kembali nanti."
        db.session.commit()
        return refund
