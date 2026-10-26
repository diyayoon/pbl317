"""Aturan status pesanan: transisi sah, pembatalan (stok kembali), dan kedaluwarsa."""
from datetime import datetime, timedelta, timezone
from flask import current_app
from sqlalchemy import select
from app.extensions import db
from app.models import Order, Product, User
from app.utils import audit

STATUS = ("Menunggu pembayaran", "Menunggu persetujuan", "Diproses", "Dikirim", "Selesai", "Dibatalkan")
TRANSISI = {
    "Menunggu pembayaran": {"Dibatalkan"},
    "Menunggu persetujuan": {"Dibatalkan"},
    "Diproses": {"Dikirim"},
    "Dikirim": {"Selesai"},
    "Selesai": set(),
    "Dibatalkan": set(),
}
TERBUKA = ("Menunggu pembayaran", "Menunggu persetujuan")


class LayananPesanan:
    @staticmethod
    def kembalikan_stok(order: Order) -> None:
        ids = [i.product_id for i in order.items if i.product_id]
        locked = {p.id: p for p in db.session.scalars(select(Product).where(Product.id.in_(ids)).with_for_update())} if ids else {}
        for item in order.items:
            produk = locked.get(item.product_id)
            if produk is not None:
                produk.stock += item.quantity

    @classmethod
    def ubah_status(cls, order: Order, status: str, admin: User) -> Order:
        if status not in STATUS:
            raise ValueError("Status pesanan tidak valid.")
        if status == order.status:
            return order
        if status not in TRANSISI.get(order.status, set()):
            raise ValueError(f"Transisi status {order.status} ke {status} tidak diizinkan.")
        if status in {"Dikirim", "Selesai"} and (not order.payment or order.payment.status != "Disetujui"):
            raise ValueError("Pesanan tidak dapat dikirim atau diselesaikan sebelum pembayaran disetujui.")
        if status == "Dibatalkan":
            cls.kembalikan_stok(order)
            if order.payment:
                order.payment.status = "Dibatalkan"
                order.payment.reviewed_by = admin.id
                order.payment.reviewed_at = datetime.now(timezone.utc)
                order.payment.review_note = "Pesanan dibatalkan oleh admin."
        order.status = status
        db.session.commit()
        return order

    @classmethod
    def batalkan_oleh_customer(cls, order_id: int, customer: User) -> Order:
        """Pelanggan membatalkan pesanannya sendiri selama belum dibayar/diajukan; stok dikembalikan."""
        order = db.session.scalar(select(Order).where(Order.id == order_id, Order.user_id == customer.id).with_for_update())
        if order is None:
            raise LookupError("Pesanan tidak ditemukan.")
        if order.status != "Menunggu pembayaran":
            raise ValueError("Pesanan ini sudah tidak bisa dibatalkan sendiri. Hubungi admin bila perlu.")
        cls.kembalikan_stok(order)
        order.status = "Dibatalkan"
        if order.payment:
            order.payment.status = "Dibatalkan"
            order.payment.review_note = "Dibatalkan oleh pelanggan."
        audit.catat("pesanan_dibatalkan_pelanggan", "order", order.id, order.order_number)
        db.session.commit()
        return order

    @classmethod
    def kedaluwarsakan(cls) -> int:
        """Batalkan pesanan yang melewati batas bayar tanpa bukti; stok dikembalikan."""
        ttl = int(current_app.config.get("ORDER_PAYMENT_TTL_JAM", 24))
        batas = datetime.now(timezone.utc) - timedelta(hours=ttl)
        kandidat = db.session.scalars(
            select(Order).where(Order.status == "Menunggu pembayaran", Order.created_at < batas).with_for_update(skip_locked=True)
        ).all()
        for order in kandidat:
            cls.kembalikan_stok(order)
            order.status = "Dibatalkan"
            if order.payment:
                order.payment.status = "Kedaluwarsa"
                order.payment.review_note = "Batas waktu pembayaran berakhir."
        if kandidat:
            db.session.commit()
        return len(kandidat)
