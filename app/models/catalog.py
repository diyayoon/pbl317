"""Entitas kategori dan produk katalog."""
import re
from datetime import datetime, timezone
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    icon = db.Column(db.String(20), nullable=False, default="✧")  # legacy, dipertahankan untuk kompatibilitas data lama
    image_url = db.Column(db.String(500), nullable=True, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    products = db.relationship("Product", back_populates="category", cascade="save-update, merge")

    def __repr__(self):
        return f"<Category {self.slug}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    slug = db.Column(db.String(160), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    price = db.Column(db.Numeric(14, 0), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    era = db.Column(db.String(32), nullable=False, default="")
    origin = db.Column(db.String(100), nullable=False, default="")
    material = db.Column(db.String(100), nullable=False, default="")
    condition = db.Column(db.String(32), nullable=False, default="Good")
    authenticity_status = db.Column(db.String(32), nullable=False, default="Not verified")
    image_alt = db.Column(db.String(200), nullable=False, default="")
    image_source = db.Column(db.String(1000), nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    category = db.relationship("Category", back_populates="products")
    images = db.relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.position")
    cart_items = db.relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem", back_populates="product")
    reviews = db.relationship("Review", back_populates="product", cascade="all, delete-orphan")

    @property
    def gambar(self) -> str:
        image = next((item for item in self.images if item.is_primary), None)
        image = image or (self.images[0] if self.images else None)
        return image.image_url if image else ""

    @property
    def alt_gambar(self) -> str:
        return self.image_alt or f"Foto {self.name}"

    @property
    def sumber_gambar(self) -> str:
        return self.image_source or self.gambar

    @property
    def nama(self) -> str:
        return self.name

    @property
    def kategori(self) -> str:
        return self.category.name if self.category else "Lainnya"

    @property
    def slug_kategori(self) -> str:
        return self.category.slug if self.category else "other"

    @property
    def era_id(self) -> str:
        return self.era

    @property
    def asal(self) -> str:
        return self.origin

    @property
    def kondisi(self) -> str:
        return self.condition

    @property
    def material_id(self) -> str:
        return self.material

    @property
    def harga(self) -> int:
        return int(self.price or 0)

    @property
    def stok(self) -> int:
        return int(self.stock or 0)

    @property
    def autentikasi(self) -> str:
        return self.authenticity_status

    @property
    def deskripsi(self) -> str:
        return self.description

    @property
    def ulasan_terlihat(self) -> list:
        return [review for review in self.reviews if not review.is_hidden]

    @property
    def rating(self) -> float:
        ratings = [review.rating for review in self.ulasan_terlihat]
        return round(sum(ratings) / len(ratings), 1) if ratings else 0.0

    @property
    def ulasan(self) -> int:
        return len(self.ulasan_terlihat)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "nama": self.nama, "name": self.name, "slug": self.slug,
            "kategori": self.kategori, "slug_kategori": self.slug_kategori,
            "category_id": self.category_id, "era": self.era, "asal": self.origin,
            "kondisi": self.condition, "material": self.material, "harga": self.harga,
            "stok": self.stock, "rating": self.rating, "ulasan": self.ulasan,
            "autentikasi": self.authenticity_status, "deskripsi": self.description,
            "gambar": self.gambar, "alt_gambar": self.alt_gambar,
            "sumber_gambar": self.sumber_gambar, "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<Product {self.id} {self.slug}>"


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = db.Column(db.Text, nullable=False)
    alt_text = db.Column(db.String(200), nullable=False, default="")
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    position = db.Column(db.Integer, nullable=False, default=0)

    product = db.relationship("Product", back_populates="images")


def slugify(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:150] or "produk-antik"


__all__ = ["Category", "Product", "ProductImage", "slugify"]
