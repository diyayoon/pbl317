"""Laporan penjualan admin dihitung dari transaksi di database."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.extensions import db
from app.models import Order, OrderItem, Product, Review, User


class LayananLaporan:
    STOK_RENDAH = 2
    NAMA_BULAN = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")

    def buat_ringkasan(self):
        status_counts = dict(db.session.execute(
            select(Order.status, func.count(Order.id)).group_by(Order.status)
        ).all())
        pesanan_selesai = Order.query.filter_by(status="Selesai").all()
        pendapatan = sum(int(order.total or 0) for order in pesanan_selesai)
        produk_terjual = db.session.scalar(
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.status == "Selesai")
        ) or 0
        terlaris = db.session.execute(
            select(OrderItem.product_name_snapshot, func.sum(OrderItem.quantity).label("qty"))
            .join(Order).where(Order.status == "Selesai")
            .group_by(OrderItem.product_name_snapshot)
            .order_by(func.sum(OrderItem.quantity).desc()).limit(5)
        ).all()

        now = datetime.now(timezone.utc)
        months = []
        for offset in range(5, -1, -1):
            index = now.year * 12 + (now.month - 1) - offset
            year, month_index = divmod(index, 12)
            month = month_index + 1
            months.append({
                "kunci": f"{year:04d}-{month:02d}",
                "bulan": f"{self.NAMA_BULAN[month - 1]} {year}",
                "pendapatan": 0,
                "pesanan": 0,
            })
        monthly_index = {item["kunci"]: item for item in months}
        for order in pesanan_selesai:
            created = order.created_at
            if created:
                key = f"{created.year:04d}-{created.month:02d}"
                if key in monthly_index:
                    monthly_index[key]["pendapatan"] += int(order.total or 0)
                    monthly_index[key]["pesanan"] += 1

        return {
            "produk": Product.query.filter_by(is_active=True).count(),
            "produk_nonaktif": Product.query.filter_by(is_active=False).count(),
            "stok_rendah": Product.query.filter(Product.is_active.is_(True), Product.stock <= self.STOK_RENDAH).count(),
            "pengguna": User.query.filter_by(role="customer").count(),
            "pelanggan_aktif": User.query.filter_by(role="customer", is_active=True, deleted_at=None).count(),
            "admin": User.query.filter_by(role="admin").count(),
            "pesanan": sum(status_counts.values()),
            "pendapatan": int(pendapatan),
            "produk_terjual": int(produk_terjual),
            "menunggu_pembayaran": status_counts.get("Menunggu pembayaran", 0),
            "menunggu_persetujuan": status_counts.get("Menunggu persetujuan", 0),
            "diproses": status_counts.get("Diproses", 0),
            "dikirim": status_counts.get("Dikirim", 0),
            "selesai": status_counts.get("Selesai", 0),
            "dibatalkan": status_counts.get("Dibatalkan", 0),
            "ulasan_tersembunyi": Review.query.filter_by(is_hidden=True).count(),
            "status": status_counts,
            "bulanan": months,
            "terlaris": [{"nama": nama, "terjual": int(jumlah)} for nama, jumlah in terlaris],
        }

    def daftar_pesanan(self):
        return [order.to_dict() for order in Order.query.order_by(Order.created_at.desc()).all()]
