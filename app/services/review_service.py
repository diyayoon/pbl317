"""Ulasan produk: hanya pembeli dengan pesanan Selesai, satu ulasan per produk."""
from datetime import datetime, timezone
from sqlalchemy import select
from app.extensions import db
from app.models import Order, OrderItem, Product, Review, User


class LayananUlasan:
    @staticmethod
    def sudah_membeli(user: User, product_id: int) -> bool:
        return db.session.scalar(
            select(OrderItem.id).join(Order).where(
                Order.user_id == user.id, Order.status == "Selesai", OrderItem.product_id == product_id
            ).limit(1)
        ) is not None

    @classmethod
    def simpan(cls, user: User, payload) -> Review:
        if not isinstance(payload, dict):
            raise ValueError("Data ulasan tidak valid.")
        try:
            product_id = int(payload.get("product_id"))
            rating = int(payload.get("rating"))
        except (TypeError, ValueError):
            raise ValueError("Produk dan rating wajib diisi.")
        komentar = str(payload.get("komentar", "")).strip()
        if not 1 <= rating <= 5:
            raise ValueError("Rating harus 1 sampai 5.")
        if len(komentar) > 1000:
            raise ValueError("Komentar maksimal 1000 karakter.")
        if db.session.get(Product, product_id) is None:
            raise LookupError("Produk tidak ditemukan.")
        if not cls.sudah_membeli(user, product_id):
            raise PermissionError("Ulasan hanya dapat diberikan untuk produk dari pesanan yang sudah selesai.")
        ulasan = Review.query.filter_by(user_id=user.id, product_id=product_id).first()
        if ulasan is None:
            ulasan = Review(user_id=user.id, product_id=product_id)
            db.session.add(ulasan)
        ulasan.rating, ulasan.comment = rating, komentar
        db.session.commit()
        return ulasan

    @staticmethod
    def milik_user(user: User) -> dict[int, dict]:
        return {r.product_id: {"rating": r.rating, "komentar": r.comment, "tersembunyi": r.is_hidden}
                for r in Review.query.filter_by(user_id=user.id).all()}

    @staticmethod
    def terlihat(product_id: int, batas: int = 20) -> list[dict]:
        rows = Review.query.filter_by(product_id=product_id, is_hidden=False).order_by(Review.created_at.desc()).limit(batas).all()
        return [r.to_dict() for r in rows]

    @staticmethod
    def semua_admin() -> list[dict]:
        return [r.to_dict(admin=True) for r in Review.query.order_by(Review.created_at.desc()).limit(500).all()]

    @staticmethod
    def moderasi(review_id: int, admin: User, sembunyikan: bool, alasan: str = "") -> Review:
        ulasan = db.session.get(Review, review_id)
        if ulasan is None:
            raise LookupError("Ulasan tidak ditemukan.")
        alasan = str(alasan or "").strip()[:300]
        if sembunyikan and len(alasan) < 3:
            raise ValueError("Alasan menyembunyikan ulasan wajib diisi (minimal 3 karakter).")
        ulasan.is_hidden = bool(sembunyikan)
        ulasan.hidden_reason = alasan if sembunyikan else None
        ulasan.moderated_by = admin.id
        ulasan.moderated_at = datetime.now(timezone.utc)
        db.session.commit()
        return ulasan
