"""Model katalog: categories, products, product_images, reviews."""
from sqlalchemy import func
from ..extensions import db


class Kategori(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.BigInteger, primary_key=True)
    slug = db.Column(db.String(60), nullable=False, unique=True)
    nama = db.Column(db.String(100), nullable=False, unique=True)
    ikon = db.Column(db.String(16))
    urutan = db.Column(db.SmallInteger, nullable=False, default=0, server_default='0')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    produk = db.relationship('Produk', back_populates='kategori')


class Produk(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.BigInteger, primary_key=True)
    category_id = db.Column(db.BigInteger, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    nama = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), nullable=False, unique=True)
    deskripsi = db.Column(db.Text)
    harga = db.Column(db.Numeric(12, 2), nullable=False)
    stok = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    era = db.Column(db.String(50))
    asal = db.Column(db.String(80))
    material = db.Column(db.String(100))
    kondisi = db.Column(db.String(20), nullable=False, default='Good', server_default='Good')
    status_autentikasi = db.Column(db.String(20), nullable=False, default='Unverified', server_default='Unverified')
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    kategori = db.relationship('Kategori', back_populates='produk')
    gambar = db.relationship('GambarProduk', back_populates='produk', cascade='all, delete-orphan',
                             order_by='GambarProduk.urutan')
    ulasan = db.relationship('Ulasan', back_populates='produk', cascade='all, delete-orphan')

    def ubah_stok(self, selisih):
        """Menambah/mengurangi stok; menolak hasil negatif (enkapsulasi aturan stok)."""
        baru = self.stok + selisih
        if baru < 0:
            raise ValueError('Stok tidak mencukupi.')
        self.stok = baru

    @property
    def gambar_utama(self):
        return next((g for g in self.gambar if g.is_primary), self.gambar[0] if self.gambar else None)


class GambarProduk(db.Model):
    __tablename__ = 'product_images'

    id = db.Column(db.BigInteger, primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    file_path = db.Column(db.String(255))
    url_eksternal = db.Column(db.String(500))
    alt_text = db.Column(db.String(200))
    sumber_url = db.Column(db.String(500))
    is_primary = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    urutan = db.Column(db.SmallInteger, nullable=False, default=0, server_default='0')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    produk = db.relationship('Produk', back_populates='gambar')

    @property
    def url(self):
        """URL eksternal bila ada; file upload disajikan lewat route khusus (bukan static)."""
        return self.url_eksternal


class Ulasan(db.Model):
    __tablename__ = 'reviews'
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='uq_reviews_user_produk'),)

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    rating = db.Column(db.SmallInteger, nullable=False)
    komentar = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    produk = db.relationship('Produk', back_populates='ulasan')
    pengguna = db.relationship('Pengguna')
