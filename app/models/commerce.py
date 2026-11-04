"""Entitas keranjang, pesanan, pembayaran, dan ulasan."""
from datetime import datetime, timedelta, timezone
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Cart(db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    user = db.relationship("User", back_populates="cart")
    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan", order_by="CartItem.id")


class CartItem(db.Model):
    __tablename__ = "cart_items"
    __table_args__ = (db.UniqueConstraint("cart_id", "product_id", name="uq_cart_item_product"),)
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    selected = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    cart = db.relationship("Cart", back_populates="items")
    product = db.relationship("Product", back_populates="cart_items")

    def to_dict(self):
        product = self.product
        item = product.to_dict()
        item.update({"jumlah": self.quantity, "dipilih": self.selected})
        return item


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = db.Column(db.String(40), nullable=False, default="Menunggu pembayaran", index=True)
    payment_method = db.Column(db.String(30), nullable=False)
    subtotal = db.Column(db.Numeric(14, 0), nullable=False)
    shipping_cost = db.Column(db.Numeric(14, 0), nullable=False, default=0)
    total = db.Column(db.Numeric(14, 0), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    recipient_phone = db.Column(db.String(20), nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    address_snapshot = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id")
    payment = db.relationship("Payment", back_populates="order", uselist=False, cascade="all, delete-orphan")

    @property
    def batas_bayar(self):
        from flask import current_app
        jam = int(current_app.config.get("ORDER_PAYMENT_TTL_JAM", 24))
        return self.created_at + timedelta(hours=jam)

    def to_dict(self):
        payment = self.payment
        bukti = None
        if payment and payment.original_filename:
            bukti = {
                "id": payment.id, "namaFile": payment.original_filename,
                "url": f"/media/payments/{payment.id}",
                "tanggal": payment.uploaded_at.isoformat() if payment.uploaded_at else None,
                "status": payment.status, "catatan": payment.review_note or "",
            }
        return {
            "id": self.id, "orderNumber": self.order_number, "date": self.created_at.isoformat(),
            "status": self.status, "pembayaran": self.payment_method, "total": int(self.total or 0), "ongkir": int(self.shipping_cost or 0),
            "statusPembayaran": payment.status if payment else "Menunggu pembayaran",
            "batasBayar": self.batas_bayar.isoformat(),
            "nama": self.recipient_name, "telepon": self.recipient_phone,
            "alamat": self.shipping_address, "alamatPengiriman": self.address_snapshot,
            "items": [item.to_dict() for item in self.items],
            "buktiBayar": bukti,
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name_snapshot = db.Column(db.String(120), nullable=False)
    product_image_snapshot = db.Column(db.Text, nullable=False, default="")
    unit_price = db.Column(db.Numeric(14, 0), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    def to_dict(self):
        return {"id": self.product_id, "orderItemId": self.id, "nama": self.product_name_snapshot, "harga": int(self.unit_price), "gambar": self.product_image_snapshot, "jumlah": self.quantity}


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="Menunggu pembayaran", index=True)
    proof_path = db.Column(db.String(500), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    review_note = db.Column(db.String(500), nullable=True)
    # Payment gateway (Midtrans). Token/URL Snap hanya tautan sekali-bayar; kunci server tidak pernah disimpan.
    snap_redirect_url = db.Column(db.String(500), nullable=True)
    gateway_status = db.Column(db.String(30), nullable=True)
    gateway_payment_type = db.Column(db.String(40), nullable=True)
    gateway_transaction_id = db.Column(db.String(64), nullable=True)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)
    order = db.relationship("Order", back_populates="payment")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id, "order_id": self.order_id,
            "order_number": self.order.order_number if self.order else "",
            "customer": self.order.user.nama if self.order and self.order.user else "",
            "email": self.order.user.email if self.order and self.order.user else "",
            "file_name": self.original_filename or "", "status": self.status,
            "bukti_url": f"/media/payments/{self.id}" if self.proof_path else "",
            "catatan": self.review_note or "",
            "total": int(self.order.total or 0) if self.order else 0,
            "method": self.method, "gateway_status": self.gateway_status or "",
            "gateway_payment_type": self.gateway_payment_type or "",
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (db.UniqueConstraint("order_item_id", name="uq_reviews_order_item"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_items.id", ondelete="SET NULL"), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False, default="")
    image_path = db.Column(db.String(500), nullable=True)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False, index=True)
    hidden_reason = db.Column(db.String(300), nullable=True)
    moderated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    user = db.relationship("User", back_populates="reviews", foreign_keys=[user_id])
    product = db.relationship("Product", back_populates="reviews")
    order_item = db.relationship("OrderItem", foreign_keys=[order_item_id])
    moderator = db.relationship("User", foreign_keys=[moderated_by])

    def to_dict(self, admin: bool = False):
        data = {
            "id": self.id, "produk_id": self.product_id, "order_item_id": self.order_item_id, "rating": self.rating,
            "komentar": self.comment, "tanggal": self.created_at.isoformat(),
            "nama": self.user.nama if self.user else "Pelanggan",
            "foto": self.user.avatar_data if self.user else None,
            "gambar_url": f"/media/reviews/{self.id}" if self.image_path else "",
        }
        if admin:
            data.update({
                "produk": self.product.name if self.product else "(produk dihapus)",
                "email": self.user.email if self.user else "", "tersembunyi": self.is_hidden,
                "alasan": self.hidden_reason or "",
            })
        return data


class RefundRequest(db.Model):
    """Permintaan pengembalian dana Midtrans yang ditinjau admin dan disinkronkan ke gateway."""
    __tablename__ = "refund_requests"
    __table_args__ = (
        db.Index("ix_refund_requests_status_created", "status", "requested_at"),
        db.Index("ix_refund_requests_order", "order_id", "requested_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Numeric(14, 0), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Menunggu persetujuan", index=True)
    refund_key = db.Column(db.String(100), nullable=False, unique=True)
    gateway_status = db.Column(db.String(40), nullable=True)
    gateway_refund_id = db.Column(db.String(100), nullable=True)
    gateway_payment_type = db.Column(db.String(40), nullable=True)
    admin_note = db.Column(db.String(500), nullable=True)
    requested_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order", foreign_keys=[order_id])
    user = db.relationship("User", foreign_keys=[user_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id, "order_id": self.order_id,
            "order_number": self.order.order_number if self.order else "",
            "customer": self.user.nama if self.user else "Pelanggan",
            "email": self.user.email if self.user else "",
            "reason": self.reason, "amount": int(self.amount or 0),
            "status": self.status, "gateway_status": self.gateway_status or "",
            "payment_type": self.gateway_payment_type or (self.order.payment.gateway_payment_type if self.order and self.order.payment else ""),
            "admin_note": self.admin_note or "",
            "requested_at": self.requested_at.isoformat() if self.requested_at else "",
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else "",
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
        }
