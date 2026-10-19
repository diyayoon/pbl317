"""Kelola kategori produk (admin)."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Category, Product
from app.models.catalog import slugify


class LayananKategori:
    @staticmethod
    def daftar() -> list[dict]:
        jumlah = dict(db.session.execute(
            select(Product.category_id, func.count(Product.id)).group_by(Product.category_id)
        ).all())
        return [
            {"id": c.id, "nama": c.name, "slug": c.slug, "ikon": c.icon, "aktif": c.is_active,
             "jumlah_produk": int(jumlah.get(c.id, 0))}
            for c in Category.query.order_by(Category.id.asc()).all()
        ]

    @staticmethod
    def _validasi(payload):
        if not isinstance(payload, dict):
            raise ValueError("Data kategori tidak valid.")
        nama = " ".join(str(payload.get("nama", "")).split())
        ikon = str(payload.get("ikon", "") or "✧").strip()
        if not 3 <= len(nama) <= 80:
            raise ValueError("Nama kategori harus 3–80 karakter.")
        if len(ikon) > 8:
            raise ValueError("Ikon maksimal 8 karakter (satu emoji).")
        return nama, ikon

    @classmethod
    def tambah(cls, payload) -> Category:
        nama, ikon = cls._validasi(payload)
        if Category.query.filter(func.lower(Category.name) == nama.lower()).first():
            raise ValueError("Nama kategori sudah dipakai.")
        base = slugify(nama)
        slug, i = base, 2
        while Category.query.filter_by(slug=slug).first():
            slug, i = f"{base}-{i}", i + 1
        kategori = Category(name=nama, slug=slug, icon=ikon, is_active=True)
        try:
            db.session.add(kategori)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Kategori bentrok dengan data lain.")
        return kategori

    @classmethod
    def ubah(cls, kategori: Category, payload) -> Category:
        nama, ikon = cls._validasi(payload)
        bentrok = Category.query.filter(func.lower(Category.name) == nama.lower(), Category.id != kategori.id).first()
        if bentrok:
            raise ValueError("Nama kategori sudah dipakai.")
        kategori.name, kategori.icon = nama, ikon
        if "aktif" in payload:
            kategori.is_active = bool(payload["aktif"])
        db.session.commit()
        return kategori

    @classmethod
    def hapus(cls, kategori: Category) -> str:
        """Hapus bila kosong; bila masih dipakai produk, kategori dinonaktifkan."""
        dipakai = db.session.scalar(select(func.count(Product.id)).where(Product.category_id == kategori.id)) or 0
        if dipakai:
            kategori.is_active = False
            db.session.commit()
            return "dinonaktifkan"
        db.session.delete(kategori)
        db.session.commit()
        return "dihapus"
