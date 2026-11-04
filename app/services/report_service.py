"""Laporan penjualan dengan filter tanggal berdasarkan waktu lokal Indonesia (WIB)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.extensions import db
from app.models import Order, OrderItem, Product, Review, User

WIB = ZoneInfo("Asia/Jakarta")


class LayananLaporan:
    STOK_RENDAH = 2
    NAMA_BULAN = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")

    @staticmethod
    def _rentang_utc(tanggal_awal: date | None, tanggal_akhir: date | None):
        awal = datetime.combine(tanggal_awal, time.min, WIB).astimezone(timezone.utc) if tanggal_awal else None
        akhir = datetime.combine(tanggal_akhir + timedelta(days=1), time.min, WIB).astimezone(timezone.utc) if tanggal_akhir else None
        return awal, akhir

    def buat_ringkasan(self, tanggal_awal: date | None = None, tanggal_akhir: date | None = None, include_transactions: bool = True):
        awal, akhir = self._rentang_utc(tanggal_awal, tanggal_akhir)
        kondisi = []
        if awal:
            kondisi.append(Order.created_at >= awal)
        if akhir:
            kondisi.append(Order.created_at < akhir)
        semua = Order.query.filter(*kondisi).all()
        status_counts = {}
        for order in semua:
            status_counts[order.status] = status_counts.get(order.status, 0) + 1
        selesai = [order for order in semua if order.status == "Selesai"]
        ids_selesai = [order.id for order in selesai]
        pendapatan = sum(int(order.total or 0) for order in selesai)
        produk_terjual = db.session.scalar(
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.id.in_(ids_selesai))
        ) or 0
        terlaris_rows = db.session.execute(
            select(OrderItem.product_name_snapshot, func.sum(OrderItem.quantity).label("qty"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.id.in_(ids_selesai))
            .group_by(OrderItem.product_name_snapshot)
            .order_by(func.sum(OrderItem.quantity).desc()).limit(10)
        ).all() if ids_selesai else []

        now = datetime.now(WIB)
        months = []
        for offset in range(5, -1, -1):
            index = now.year * 12 + (now.month - 1) - offset
            year, month_index = divmod(index, 12)
            month = month_index + 1
            months.append({"kunci": f"{year:04d}-{month:02d}", "bulan": f"{self.NAMA_BULAN[month - 1]} {year}", "pendapatan": 0, "pesanan": 0})
        monthly_index = {item["kunci"]: item for item in months}
        for order in selesai:
            created = order.created_at
            if created:
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                local = created.astimezone(WIB)
                key = f"{local.year:04d}-{local.month:02d}"
                if key in monthly_index:
                    monthly_index[key]["pendapatan"] += int(order.total or 0)
                    monthly_index[key]["pesanan"] += 1

        return {
            "tanggal_awal": tanggal_awal.isoformat() if tanggal_awal else "",
            "tanggal_akhir": tanggal_akhir.isoformat() if tanggal_akhir else "",
            "produk": Product.query.filter_by(is_active=True).count(),
            "produk_nonaktif": Product.query.filter_by(is_active=False).count(),
            "stok_rendah": Product.query.filter(Product.is_active.is_(True), Product.stock <= self.STOK_RENDAH).count(),
            "pengguna": User.query.filter_by(role="customer").count(),
            "pelanggan_aktif": User.query.filter_by(role="customer", is_active=True, deleted_at=None).count(),
            "admin": User.query.filter_by(role="admin").count(),
            "pesanan": len(semua),
            "pendapatan": int(pendapatan),
            "produk_terjual": int(produk_terjual),
            "menunggu_pembayaran": status_counts.get("Menunggu pembayaran", 0),
            "menunggu_persetujuan": status_counts.get("Menunggu persetujuan", 0),
            "diproses": status_counts.get("Diproses", 0),
            "dikirim": status_counts.get("Dikirim", 0),
            "selesai": status_counts.get("Selesai", 0),
            "dibatalkan": status_counts.get("Dibatalkan", 0),
            "direfund": status_counts.get("Direfund", 0),
            "ulasan_tersembunyi": Review.query.filter_by(is_hidden=True).count(),
            "status": status_counts,
            "bulanan": months,
            "terlaris": [{"nama": nama, "terjual": int(jumlah)} for nama, jumlah in terlaris_rows],
            "transaksi_selesai": ([self._baris_order(order) for order in sorted(selesai, key=lambda o: o.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)] if include_transactions else []),
        }

    @staticmethod
    def _baris_order(order: Order) -> dict:
        created = order.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created:
            created = created.astimezone(WIB)
        return {
            "order_number": order.order_number,
            "tanggal": created.strftime("%d-%m-%Y %H:%M") if created else "",
            "customer": order.user.nama if order.user else "Pelanggan",
            "email": order.user.email if order.user else "",
            "status": order.status,
            "metode": order.payment_method,
            "total": int(order.total or 0),
        }

    def daftar_pesanan(self):
        return [order.to_dict() for order in Order.query.order_by(Order.created_at.desc()).all()]
