"""Laporan admin dihitung langsung dari PostgreSQL (satu definisi pendapatan: pesanan Selesai)."""
from sqlalchemy import func, select
from app.extensions import db
from app.models import Order, OrderItem, Product, Review, User


class LayananLaporan:
    STOK_RENDAH = 2

    def buat_ringkasan(self):
        status_counts = dict(db.session.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all())
        pendapatan = db.session.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == "Selesai")) or 0
        terlaris = db.session.execute(
            select(OrderItem.product_name_snapshot, func.sum(OrderItem.quantity).label("qty"))
            .join(Order).where(Order.status.in_(("Diproses", "Dikirim", "Selesai")))
            .group_by(OrderItem.product_name_snapshot).order_by(func.sum(OrderItem.quantity).desc()).limit(5)
        ).all()
        return {
            "produk": Product.query.filter_by(is_active=True).count(),
            "produk_nonaktif": Product.query.filter_by(is_active=False).count(),
            "stok_rendah": Product.query.filter(Product.is_active.is_(True), Product.stock <= self.STOK_RENDAH).count(),
            "pengguna": User.query.filter_by(role="customer").count(),
            "admin": User.query.filter_by(role="admin").count(),
            "pesanan": sum(status_counts.values()),
            "pendapatan": int(pendapatan),
            "menunggu_pembayaran": status_counts.get("Menunggu pembayaran", 0),
            "menunggu_persetujuan": status_counts.get("Menunggu persetujuan", 0),
            "diproses": status_counts.get("Diproses", 0),
            "dikirim": status_counts.get("Dikirim", 0),
            "selesai": status_counts.get("Selesai", 0),
            "dibatalkan": status_counts.get("Dibatalkan", 0),
            "ulasan_tersembunyi": Review.query.filter_by(is_hidden=True).count(),
            "status": status_counts,
            "terlaris": [{"nama": n, "terjual": int(q)} for n, q in terlaris],
        }

    def daftar_pesanan(self):
        return [order.to_dict() for order in Order.query.order_by(Order.created_at.desc()).all()]
