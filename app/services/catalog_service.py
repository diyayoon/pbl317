"""Aturan bisnis katalog; semua CRUD database dilakukan dalam satu lapisan OOP."""
from __future__ import annotations
from pathlib import Path
from flask import current_app
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Category, OrderItem, Product, ProductImage
from app.models.catalog import slugify


class CatalogService:
    ERA = {"1800s", "1900–1949", "1950–1999", "2000–sekarang"}
    KONDISI = {"Excellent", "Good", "Fair", "Needs restoration"}
    AUTENTIKASI = {"Verified", "Documented", "Inspected", "Not verified"}

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

    MAKS_KATA = 6
    MAKS_PANJANG_Q = 100

    @classmethod
    def tokenisasi(cls, query: str) -> list[str]:
        """Normalisasi spasi/huruf, buang duplikat, batasi jumlah kata. Kata 1 huruf dibuang kecuali satu-satunya."""
        kata = []
        for k in " ".join(str(query or "").split())[: cls.MAKS_PANJANG_Q].lower().split(" "):
            if k and k not in kata:
                kata.append(k[:40])
        panjang = [k for k in kata if len(k) > 1]
        return (panjang or kata)[: cls.MAKS_KATA]

    @staticmethod
    def _pola(kata: str) -> str:
        return "%" + kata.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    @classmethod
    def cari(cls, query: str, category_slug: str = "", active_only: bool = True, limit: int = 200) -> list[dict]:
        """Pencarian ke PostgreSQL (ILIKE terparameter). Produk dengan lebih banyak kata cocok tampil lebih dulu,
        lalu berdasarkan bobot bidang (nama > kategori > material/asal/era > kondisi/deskripsi), lalu terbaru."""
        kata = cls.tokenisasi(query)
        if not kata:
            return cls.list_products(category_slug=category_slug, active_only=active_only)
        bidang = [(Product.name, 5), (Category.name, 3), (Product.material, 2), (Product.origin, 2),
                  (Product.era, 2), (Product.condition, 1), (Product.description, 1)]
        jumlah_cocok, skor = 0, 0
        for k in kata:
            pola = cls._pola(k)
            jumlah_cocok = jumlah_cocok + case((or_(*[f.ilike(pola, escape="\\") for f, _ in bidang]), 1), else_=0)
            for f, bobot in bidang:
                skor = skor + case((f.ilike(pola, escape="\\"), bobot), else_=0)
        frasa = cls._pola(" ".join(kata))
        skor = skor + case((Product.name.ilike(frasa, escape="\\"), 10), else_=0)  # bonus frasa utuh di nama
        statement = (select(Product).join(Category, Product.category_id == Category.id)
                     .options(selectinload(Product.images), selectinload(Product.category), selectinload(Product.reviews))
                     .where(jumlah_cocok >= 1))
        if active_only:
            statement = statement.where(Product.is_active.is_(True))
        if category_slug:
            statement = statement.where(Category.slug == category_slug)
        statement = statement.order_by(jumlah_cocok.desc(), skor.desc(), Product.id.desc()).limit(limit)
        return [product.to_dict() for product in db.session.scalars(statement).unique().all()]

    @classmethod
    def list_products(cls, query: str = "", category_slug: str = "", active_only: bool = True) -> list[dict]:
        if query.strip():
            return cls.cari(query, category_slug, active_only)
        statement = select(Product).options(
            selectinload(Product.images), selectinload(Product.category), selectinload(Product.reviews)
        ).order_by(Product.id.desc())
        if active_only:
            statement = statement.where(Product.is_active.is_(True))
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
        gambar_bawaan = {
            "timepiece": "/static/images/categories/jam-timepiece.jpg",
            "camera": "/static/images/categories/kamera-vintage.jpg",
            "porcelain": "/static/images/categories/porselen-keramik.jpg",
            "books": "/static/images/categories/buku-manuskrip.jpg",
            "jewelry": "/static/images/categories/perhiasan-antik.jpg",
            "music": "/static/images/categories/musik-vintage.jpg",
            "decor": "/static/images/categories/dekorasi-interior.jpg",
            "travel": "/static/images/categories/travel-collectibles.jpg",
        }
        results = []
        for category in categories:
            products = [item for item in category.products if item.is_active]
            foto_produk = next((item.gambar for item in products if item.gambar), "")
            gambar_khusus = (category.image_url or "").strip()
            gambar_placeholder = gambar_khusus.lower().endswith(".svg") or "/assets/categories/" in gambar_khusus.lower()
            if gambar_placeholder:
                gambar_khusus = ""
            cover = (
                gambar_khusus
                or gambar_bawaan.get(category.slug)
                or foto_produk
                or "/static/images/categories/jam-timepiece.jpg"
            )
            results.append({
                "id": category.id, "slug": category.slug, "nama": category.name,
                "ikon": category.icon, "jumlah": len(products), "gambar": cover,
            })
        return results

    @classmethod
    def normalize_payload(cls, payload, existing: Product | None = None, image_url: str = ""):
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
        image = str(image_url or "").strip()
        if image and not image.startswith("/media/products/"):
            errors["gambar"] = "Lokasi foto produk tidak valid."
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
    def create_product(cls, payload, image_url: str = ""):
        values, errors = cls.normalize_payload(payload, image_url=image_url)
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
            if values["image"]:
                product.images.append(ProductImage(image_url=values["image"], alt_text=values["image_alt"], is_primary=True, position=0))
            db.session.add(product)
            db.session.commit()
            return product, {}
        except IntegrityError:
            db.session.rollback()
            return None, {"umum": "Data produk bentrok dengan data lain. Coba lagi."}

    @classmethod
    def update_product(cls, product: Product, payload, image_url: str = ""):
        values, errors = cls.normalize_payload(payload, existing=product, image_url=image_url)
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
                primary = next((image for image in product.images if image.is_primary), None)
                if primary is None:
                    primary = ProductImage(product=product, is_primary=True, position=0)
                    db.session.add(primary)
                primary.image_url = new_image
                primary.alt_text = values["image_alt"]
            db.session.commit()
            return product, {}
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
