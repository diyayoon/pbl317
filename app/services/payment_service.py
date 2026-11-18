"""Layanan bukti pembayaran dan persetujuan admin."""
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import current_app
from sqlalchemy import select
from app.extensions import db
from app.models import Order, Payment, User
from app.utils.uploads import ekstensi_file_diizinkan


class LayananPembayaran:
    def __init__(self, customer: User | None = None):
        self.customer = customer

    def simpan_bukti(self, order: Order, file):
        if not order or order.user_id != self.customer.id:
            raise LookupError("Pesanan tidak ditemukan pada akun ini.")
        if order.payment_method == "Midtrans":
            raise ValueError("Pesanan Midtrans dibayar lewat tombol Bayar sekarang, bukan unggah bukti.")
        if order.status not in {"Menunggu pembayaran", "Menunggu persetujuan"}:
            raise ValueError("Pesanan ini tidak menerima bukti pembayaran baru.")
        if not file or not file.filename:
            raise ValueError("Pilih file bukti pembayaran terlebih dahulu.")
        original = secure_filename(file.filename)
        extension = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        if not ekstensi_file_diizinkan(original, current_app.config["PAYMENT_ALLOWED_EXTENSIONS"]):
            raise ValueError("Bukti bayar harus JPG, JPEG, PNG, WEBP, atau PDF.")
        batas = current_app.config["PAYMENT_MAX_BYTES"]
        raw = file.stream.read(batas + 1)
        if not raw or len(raw) > batas:
            raise ValueError("Ukuran bukti bayar maksimal 5 MB.")
        signatures = {
            "jpg": raw.startswith(b"\xff\xd8\xff"), "jpeg": raw.startswith(b"\xff\xd8\xff"),
            "png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
            "webp": len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP",
            "pdf": raw.startswith(b"%PDF-"),
        }
        if not signatures.get(extension, False):
            raise ValueError("Isi file tidak sesuai dengan ekstensi yang dipilih.")
        folder = Path(current_app.config["PAYMENT_UPLOAD_FOLDER"]).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}.{extension}"
        path = folder / stored_name
        old_path = Path(order.payment.proof_path).resolve() if order.payment and order.payment.proof_path else None
        path.write_bytes(raw)
        payment = order.payment or Payment(order=order, method=order.payment_method)
        payment.proof_path = str(path)
        payment.original_filename = f"{uuid4().hex[:8]}-{original}"[:255]
        payment.uploaded_at = datetime.now(timezone.utc)
        payment.status = "Menunggu persetujuan"
        payment.reviewed_by = None
        payment.reviewed_at = None
        payment.review_note = None
        order.status = "Menunggu persetujuan"
        db.session.add(payment)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            path.unlink(missing_ok=True)
            raise
        if old_path and old_path != path and folder in old_path.parents and old_path.is_file():
            try:
                old_path.unlink()
            except OSError:
                current_app.logger.warning("Gagal menghapus bukti pembayaran lama %s", old_path.name)
        return payment

    @staticmethod
    def tinjau(payment_id: int, admin: User, action: str, note: str = ""):
        payment = db.session.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if not payment:
            raise LookupError("Pembayaran tidak ditemukan.")
        if action not in {"approve", "reject"}:
            raise ValueError("Aksi pembayaran tidak valid.")
        note = str(note or "").strip()
        if action == "reject" and len(note) < 3:
            raise ValueError("Alasan penolakan wajib diisi (minimal 3 karakter).")
        if not payment.proof_path:
            raise ValueError("Pembayaran belum memiliki file bukti yang tersimpan.")
        if payment.status != "Menunggu persetujuan" or not payment.order or payment.order.status != "Menunggu persetujuan":
            raise ValueError("Pembayaran hanya dapat ditinjau ketika pesanan menunggu persetujuan.")
        payment.reviewed_by = admin.id
        payment.reviewed_at = datetime.now(timezone.utc)
        payment.review_note = note[:500]
        if action == "approve":
            payment.status = "Disetujui"
            payment.order.status = "Diproses"
        else:
            payment.status = "Ditolak"
            payment.order.status = "Menunggu pembayaran"
        db.session.commit()
        return payment
