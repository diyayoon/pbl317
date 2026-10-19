"""Aturan bisnis katalog; semua CRUD database dilakukan dalam satu lapisan OOP."""
from __future__ import annotations
import base64
import binascii
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from flask import current_app
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Category, OrderItem, Product, ProductImage, Review
from app.models.catalog import slugify


class CatalogService:
    ERA = {"1800s", "1900–1949", "1950–1999", "2000–sekarang"}
    KONDISI = {"Excellent", "Good", "Fair", "Needs restoration"}
    AUTENTIKASI = {"Verified", "Documented", "Inspected", "Not verified"}
    DATA_IMAGE_PATTERN = re.compile(r"^data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=\r\n]+)$")

    @staticmethod
    def slug_unik(name: str, exclude_id: int | None = None) -> str:
        base = slugify(name)
        slug = base
        index = 2
        while True:
            query = Product.query.filter_by(slug=slug)
            if exclude_id is not None:
                query = query.filter(Product.id != exclude_id)
            if query.first() is None:
                return slug
            slug = f"{base}-{index}"
            index += 1

    @classmethod
    def list_products(cls, query: str = "", category_slug: str = "", active_only: bool = True) -> list[dict]:
        statement = select(Product).options(
            selectinload(Product.images), selectinload(Product.category), selectinload(Product.reviews)
        ).order_by(Product.id.desc())
        if active_only:
            statement = statement.where(Product.is_active.is_(True))
        if query.strip():
            esc = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            needle = f"%{esc}%"
            statement = statement.where(or_(
                Product.name.ilike(needle, escape="\\"), Product.description.ilike(needle, escape="\\"),
                Product.origin.ilike(needle, escape="\\"),
            ))
        if category_slug:
            statement = statement.join(Category).where(Category.slug == category_slug)
        return [product.to_dict() for product in db.session.scalars(statement).unique().all()]

    @classmethod
    def get_product(cls, product_id: int, active_only: bool = True) -> Product | None:
        query = Product.query.filter_by(id=product_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.first()

    @classmethod
    def category_summary(cls) -> list[dict]:
        categories = db.session.scalars(
            select(Category).where(Category.is_active.is_(True)).options(
                selectinload(Category.products).selectinload(Product.images)
            ).order_by(Category.id.asc())
        ).all()
        results = []
        for category in categories:
            products = [item for item in category.products if item.is_active]
            cover = next((p.gambar for p in products if p.gambar), "")
            results.append({
                "id": category.id, "slug": category.slug, "nama": category.name,
                "ikon": category.icon, "jumlah": len(products), "gambar": cover,
            })
        return results

    @classmethod
    def normalize_payload(cls, payload, existing: Product | None = None):
        if not isinstance(payload, dict):
            return None, {"umum": "Data produk tidak valid."}
        errors = {}

        def text_field(key, label, maximum, required=True):
            value = payload.get(key, "")
            value = value.strip() if isinstance(value, str) else ""
            if required and not value:
                errors[key] = f"{label} wajib diisi."
            elif len(value) > maximum:
                errors[key] = f"{label} maksimal {maximum} karakter."
            return value

        name = text_field("nama", "Nama produk", 120)
        if name and len(name) < 3:
            errors["nama"] = "Nama produk minimal 3 karakter."
        category_name = text_field("kategori", "Kategori", 80)
        category = Category.query.filter_by(name=category_name, is_active=True).first() if category_name else None
        if category_name and category is None:
            errors["kategori"] = "Pilih kategori yang tersedia."
        era = text_field("era", "Era", 32)
        if era not in cls.ERA:
            errors["era"] = "Pilih era yang tersedia."
        origin = text_field("asal", "Asal", 100)
        condition = text_field("kondisi", "Kondisi", 32)
        if condition not in cls.KONDISI:
            errors["kondisi"] = "Pilih kondisi yang tersedia."
        material = text_field("material", "Material", 100)
        authenticity = text_field("autentikasi", "Status autentikasi", 32)
        if authenticity not in cls.AUTENTIKASI:
            errors["autentikasi"] = "Pilih status autentikasi yang tersedia."
        description = text_field("deskripsi", "Deskripsi", 4000, required=False)

        try:
            price = int(payload.get("harga"))
            if price < 1000 or price > 10**12:
                raise ValueError
        except (ValueError, TypeError, OverflowError):
            price = 0
            errors["harga"] = "Harga minimum Rp1.000 dan harus berupa angka bulat yang valid."
        try:
            stock = int(payload.get("stok"))
            if stock < 0 or stock > 10**7 or str(payload.get("stok")).strip() != str(stock):
                raise ValueError
        except (ValueError, TypeError, OverflowError):
            stock = 0
            errors["stok"] = "Stok harus bilangan bulat nonnegatif."
        image = payload.get("gambar", "")
        image = image.strip() if isinstance(image, str) else ""
        if len(image) > 2_800_000:
            errors["gambar"] = "Foto terlalu besar. Gunakan foto maksimal 2 MB."
        elif image and not image.startswith("data:"):
            parsed = urlsplit(image)
            if parsed.scheme not in {"https", "/"} and not image.startswith("/media/products/"):
                errors["gambar"] = "URL foto eksternal harus HTTPS atau path media produk."
        elif image and not cls.DATA_IMAGE_PATTERN.fullmatch(image):
            errors["gambar"] = "Format foto tidak valid. Gunakan JPG, PNG, atau WEBP."
        if errors:
            return None, errors
        return {
            "name": name, "category": category, "era": era, "origin": origin,
            "condition": condition, "material": material, "authenticity_status": authenticity,
            "description": description, "price": price, "stock": stock, "image": image,
            "image_alt": f"Foto {name}",
            "image_source": str(payload.get("sumber_gambar") or (existing.image_source if existing else ""))[:1000],
        }, {}

    @classmethod
    def _store_image(cls, image: str, alt: str) -> str:
        if not image:
            return ""
        if image.startswith("/media/products/") or image.startswith("https://"):
            return image
        match = cls.DATA_IMAGE_PATTERN.fullmatch(image)
        if not match:
            raise ValueError("Format gambar tidak diizinkan.")
        extension = match.group(1).lower()
        raw = base64.b64decode(match.group(2), validate=True)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("Ukuran gambar melebihi 2 MB.")
        signatures = {
            "png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
            "jpeg": raw.startswith(b"\xff\xd8\xff"),
            "webp": len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP",
        }
        if not signatures.get(extension, False):
            raise ValueError("Isi file tidak sesuai dengan format gambar.")
        folder = Path(current_app.config["PRODUCT_UPLOAD_FOLDER"]).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}.{ 'jpg' if extension == 'jpeg' else extension }"
        (folder / filename).write_bytes(raw)
        return f"/media/products/{filename}"

    @classmethod
    def create_product(cls, payload):
        values, errors = cls.normalize_payload(payload)
        if errors:
            return None, errors
        product = Product(
            category=values["category"], name=values["name"], slug=cls.slug_unik(values["name"]),
            description=values["description"], price=values["price"], stock=values["stock"],
            era=values["era"], origin=values["origin"], material=values["material"],
            condition=values["condition"], authenticity_status=values["authenticity_status"],
            image_alt=values["image_alt"], image_source=values["image_source"],
        )
        try:
            image_url = cls._store_image(values["image"], values["image_alt"])
            if image_url:
                product.images.append(ProductImage(image_url=image_url, alt_text=values["image_alt"], is_primary=True, position=0))
            db.session.add(product)
            db.session.commit()
            return product, {}
        except (ValueError, binascii.Error) as exc:
            db.session.rollback()
            return None, {"gambar": str(exc)}
        except IntegrityError:
            db.session.rollback()
            return None, {"umum": "Data produk bentrok dengan data lain. Coba lagi."}

    @classmethod
    def update_product(cls, product: Product, payload):
        values, errors = cls.normalize_payload(payload, existing=product)
        if errors:
            return None, errors
        new_image = values.pop("image")
        try:
            product.category = values["category"]
            product.name = values["name"]
            product.slug = cls.slug_unik(values["name"], exclude_id=product.id)
            for key in ("description", "price", "stock", "era", "origin", "material", "condition", "authenticity_status", "image_alt", "image_source"):
                setattr(product, key, values[key])
            if new_image:
                image_url = cls._store_image(new_image, values["image_alt"])
                primary = next((image for image in product.images if image.is_primary), None)
                if primary is None:
                    primary = ProductImage(product=product, is_primary=True, position=0)
                    db.session.add(primary)
                primary.image_url = image_url
                primary.alt_text = values["image_alt"]
            db.session.commit()
            return product, {}
        except (ValueError, binascii.Error) as exc:
            db.session.rollback()
            return None, {"gambar": str(exc)}
        except IntegrityError:
            db.session.rollback()
            return None, {"umum": "Perubahan produk bentrok dengan data lain. Coba lagi."}

    @classmethod
    def delete_product(cls, product: Product) -> str:
        """Hapus permanen bila belum pernah dipesan; bila sudah, nonaktifkan agar riwayat utuh.

        Mengembalikan "dihapus" atau "dinonaktifkan".
        """
        pernah_dipesan = db.session.scalar(
            select(func.count(OrderItem.id)).where(OrderItem.product_id == product.id)
        ) or 0
        if pernah_dipesan:
            product.is_active = False
            db.session.commit()
            return "dinonaktifkan"
        image_paths = [image.image_url for image in product.images if image.image_url.startswith("/media/products/")]
        db.session.delete(product)
        db.session.commit()
        base = Path(current_app.config["PRODUCT_UPLOAD_FOLDER"]).resolve()
        for image_path in image_paths:
            file_path = (base / image_path.rsplit("/", 1)[-1]).resolve()
            if base in file_path.parents and file_path.is_file():
                try:
                    file_path.unlink()
                except OSError:
                    current_app.logger.warning("Gagal menghapus file gambar produk %s", file_path.name)
        return "dihapus"

    @classmethod
    def set_active(cls, product: Product, active: bool) -> None:
        product.is_active = bool(active)
        db.session.commit()

    @classmethod
    def id_terlaris(cls, limit: int = 4) -> list[int]:
        """Produk paling laku dari pesanan yang sudah dibayar (bukan daftar ID tetap)."""
        from app.models import Order
        rows = db.session.execute(
            select(OrderItem.product_id, func.sum(OrderItem.quantity).label("qty"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.status.in_(("Diproses", "Dikirim", "Selesai")), OrderItem.product_id.is_not(None))
            .group_by(OrderItem.product_id).order_by(func.sum(OrderItem.quantity).desc()).limit(limit)
        ).all()
        return [r[0] for r in rows]
