"""Model transaksi: carts, cart_items, wishlists, orders, order_items, payments."""
from sqlalchemy import func
from ..extensions import db

STATUS_PESANAN = ('menunggu_pembayaran', 'diproses', 'dikirim', 'selesai', 'dibatalkan')
STATUS_PEMBAYARAN = ('menunggu', 'menunggu_verifikasi', 'disetujui', 'ditolak')
METODE_PEMBAYARAN = ('transfer_bank', 'qris')


class Keranjang(db.Model):
    __tablename__ = 'carts'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    pengguna = db.relationship('Pengguna', back_populates='keranjang')
    item = db.relationship('ItemKeranjang', back_populates='keranjang', cascade='all, delete-orphan')


class ItemKeranjang(db.Model):
    __tablename__ = 'cart_items'
    __table_args__ = (db.UniqueConstraint('cart_id', 'product_id', name='uq_cart_items_produk'),)

    id = db.Column(db.BigInteger, primary_key=True)
    cart_id = db.Column(db.BigInteger, db.ForeignKey('carts.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    jumlah = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    added_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    keranjang = db.relationship('Keranjang', back_populates='item')
    produk = db.relationship('Produk')


class Wishlist(db.Model):
    __tablename__ = 'wishlists'

    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='CASCADE'), primary_key=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    produk = db.relationship('Produk')


class Pesanan(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.BigInteger, primary_key=True)
    nomor_order = db.Column(db.String(30), nullable=False, unique=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    status = db.Column(db.String(25), nullable=False, default='menunggu_pembayaran', server_default='menunggu_pembayaran')
    penerima_nama = db.Column(db.String(100), nullable=False)
    penerima_telepon = db.Column(db.String(15), nullable=False)
    alamat_pengiriman = db.Column(db.String(255), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    ongkir = db.Column(db.Numeric(12, 2), nullable=False, default=0, server_default='0')
    total = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    pengguna = db.relationship('Pengguna', back_populates='pesanan')
    item = db.relationship('ItemPesanan', back_populates='pesanan', cascade='all, delete-orphan')
    pembayaran = db.relationship('Pembayaran', back_populates='pesanan', uselist=False,
                                 cascade='all, delete-orphan', foreign_keys='Pembayaran.order_id')


class ItemPesanan(db.Model):
    __tablename__ = 'order_items'
    __table_args__ = (db.UniqueConstraint('order_id', 'product_id', name='uq_order_items_produk'),)

    id = db.Column(db.BigInteger, primary_key=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True)
    nama_produk = db.Column(db.String(150), nullable=False)
    harga_satuan = db.Column(db.Numeric(12, 2), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    # Dihitung otomatis oleh PostgreSQL (harga_satuan * jumlah); jangan diisi dari Python.
    subtotal = db.Column(db.Numeric(12, 2), db.Computed('harga_satuan * jumlah', persisted=True))

    pesanan = db.relationship('Pesanan', back_populates='item')
    produk = db.relationship('Produk')


class Pembayaran(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.BigInteger, primary_key=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, unique=True)
    metode = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(25), nullable=False, default='menunggu', server_default='menunggu')
    jumlah = db.Column(db.Numeric(12, 2), nullable=False)
    bukti_path = db.Column(db.String(255))
    dibayar_pada = db.Column(db.DateTime(timezone=True))
    disetujui_oleh = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='SET NULL'))
    disetujui_pada = db.Column(db.DateTime(timezone=True))
    catatan_admin = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    pesanan = db.relationship('Pesanan', back_populates='pembayaran', foreign_keys=[order_id])
    penyetuju = db.relationship('Pengguna', foreign_keys=[disetujui_oleh])
