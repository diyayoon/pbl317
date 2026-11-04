"""Ulasan produk berdasarkan item pesanan selesai; satu ulasan per item pembelian."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select
from app.extensions import db
from app.models import Order, OrderItem, Product, Review, User
from app.utils.uploads import simpan_gambar_upload


class LayananUlasan:
    BATAS_HARI = 7

    @staticmethod
    def item_pesanan_selesai(user: User, order_item_id: int) -> OrderItem | None:
        return db.session.scalars(
            select(OrderItem).join(Order, Order.id == OrderItem.order_id).where(
                OrderItem.id == order_item_id, Order.user_id == user.id, Order.status == "Selesai"
            )
        ).first()

    @classmethod
    def bisa_direview(cls, user: User, order_item_id: int) -> bool:
        if not order_item_id or Review.query.filter_by(order_item_id=order_item_id).first():
            return False
        item = cls.item_pesanan_selesai(user, order_item_id)
        if item is None:
            return False
        selesai_pada = item.order.updated_at or item.order.created_at
        if selesai_pada.tzinfo is None:
            selesai_pada = selesai_pada.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - selesai_pada <= timedelta(days=cls.BATAS_HARI)

    @classmethod
    def simpan(cls, user: User, payload, image_file=None) -> Review:
        if not isinstance(payload, dict):
            raise ValueError("Data ulasan tidak valid.")
        try:
            order_item_id = int(payload.get("order_item_id"))
            rating = int(payload.get("rating"))
        except (TypeError, ValueError):
            raise ValueError("Item pembelian dan rating wajib diisi.")
        komentar = str(payload.get("komentar", "")).strip()
        if not 1 <= rating <= 5:
            raise ValueError("Rating harus 1 sampai 5.")
        if len(komentar) > 1000:
            raise ValueError("Komentar maksimal 1000 karakter.")
        item = cls.item_pesanan_selesai(user, order_item_id)
        if item is None or item.product_id is None:
            raise PermissionError("Ulasan hanya dapat diberikan untuk item dari pesanan yang sudah selesai milik akun ini.")
        if Review.query.filter_by(order_item_id=order_item_id).first():
            raise ValueError("Item pembelian ini sudah memiliki ulasan.")
        selesai_pada = item.order.updated_at or item.order.created_at
        if selesai_pada.tzinfo is None:
            selesai_pada = selesai_pada.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - selesai_pada > timedelta(days=cls.BATAS_HARI):
            raise PermissionError("Masa ulasan sudah berakhir. Ulasan hanya dapat dikirim maksimal 7 hari setelah pesanan selesai.")

        saved_path: Path | None = None
        try:
            if image_file and getattr(image_file, "filename", ""):
                from flask import current_app
                saved_path = simpan_gambar_upload(
                    image_file, current_app.config["REVIEW_UPLOAD_FOLDER"], current_app.config["REVIEW_MAX_BYTES"]
                )
            ulasan = Review(user_id=user.id, product_id=item.product_id, order_item_id=item.id, rating=rating,
                            comment=komentar, image_path=str(saved_path) if saved_path else None)
            db.session.add(ulasan)
            db.session.commit()
            return ulasan
        except Exception:
            db.session.rollback()
            if saved_path and saved_path.exists():
                saved_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def milik_user(user: User) -> dict[int, dict]:
        return {r.order_item_id: {"id": r.id, "rating": r.rating, "komentar": r.comment,
                                  "gambar_url": f"/media/reviews/{r.id}" if r.image_path else "",
                                  "tersembunyi": r.is_hidden}
                for r in Review.query.filter(Review.user_id == user.id, Review.order_item_id.isnot(None)).all()}

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
