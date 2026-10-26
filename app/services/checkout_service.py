from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from flask import current_app
from sqlalchemy import select
from app.extensions import db
from app.models import Address, Cart, CartItem, Order, OrderItem, Payment, Product, User
from .customer_service import LayananPelanggan


class LayananCheckout:
    METODE_BAYAR = {"Transfer Bank", "QRIS"}

    def __init__(self, customer: User):
        self.customer = customer

    @staticmethod
    def hitung_ongkir(subtotal: Decimal) -> Decimal:
        flat = Decimal(int(current_app.config.get("SHIPPING_COST_FLAT", 0)))
        gratis = Decimal(int(current_app.config.get("SHIPPING_FREE_ABOVE", 0)))
        if flat <= 0 or (gratis > 0 and subtotal >= gratis):
            return Decimal("0")
        return flat

    def data_checkout(self, direct_product_id: int | None = None, quantity: int = 1):
        if direct_product_id:
            product = Product.query.filter_by(id=direct_product_id, is_active=True).first()
            if not product:
                raise LookupError("Produk tidak ditemukan.")
            if quantity < 1 or quantity > product.stock:
                raise ValueError("Jumlah melebihi stok yang tersedia.")
            items = [dict(product.to_dict(), jumlah=quantity, dipilih=True)]
        else:
            items = [item for item in LayananPelanggan.daftar_keranjang(self.customer) if item.get("dipilih") is not False]
        subtotal = sum(Decimal(str(i.get("harga") or 0)) * int(i.get("jumlah") or 1) for i in items)
        ongkir = self.hitung_ongkir(subtotal) if items else Decimal("0")
        gratis = int(current_app.config.get("SHIPPING_FREE_ABOVE", 0))
        return {"items": items, "addresses": LayananPelanggan.daftar_alamat(self.customer),
                "ongkir": int(ongkir), "gratisOngkirDi": gratis}

    def buat_pesanan(self, address_id: int, payment_method: str, direct_product_id: int | None = None, quantity: int = 1):
        from app.services.midtrans_service import aktif as midtrans_aktif
        if payment_method not in self.METODE_BAYAR | ({"Midtrans"} if midtrans_aktif() else set()):
            raise ValueError("Metode pembayaran tidak tersedia.")
        address = Address.query.filter_by(id=address_id, user_id=self.customer.id).first()
        if not address:
            raise LookupError("Alamat pengiriman tidak ditemukan pada akun ini.")
        terbuka = Order.query.filter(Order.user_id == self.customer.id, Order.status.in_(("Menunggu pembayaran", "Menunggu persetujuan"))).count()
        if terbuka >= current_app.config.get("MAX_OPEN_ORDERS", 5):
            raise ValueError("Selesaikan atau batalkan pesanan yang masih menunggu pembayaran sebelum membuat pesanan baru.")
        cart_items_to_remove = []
        if direct_product_id:
            if quantity < 1 or quantity > 100:
                raise ValueError("Jumlah produk tidak valid.")
            products = [(db.session.scalar(select(Product).where(Product.id == direct_product_id, Product.is_active.is_(True)).with_for_update()), quantity)]
        else:
            cart = Cart.query.filter_by(user_id=self.customer.id).first()
            if not cart:
                raise ValueError("Pilih minimal satu produk di keranjang sebelum checkout.")
            # Kunci baris cart dan produk selama transaksi agar checkout serentak tidak
            # mengandalkan stok stale yang dibaca sebelum transaksi dimulai.
            cart_items_to_remove = list(db.session.scalars(
                select(CartItem).where(
                    CartItem.cart_id == cart.id, CartItem.selected.is_(True)
                ).with_for_update()
            ).all())
            if not cart_items_to_remove:
                raise ValueError("Pilih minimal satu produk di keranjang sebelum checkout.")
            product_ids = {row.product_id for row in cart_items_to_remove}
            locked_products = db.session.scalars(
                select(Product).where(Product.id.in_(product_ids)).with_for_update()
            ).all()
            product_by_id = {product.id: product for product in locked_products}
            products = [(product_by_id.get(row.product_id), row.quantity) for row in cart_items_to_remove]
        if any(product is None or not product.is_active for product, _ in products):
            raise LookupError("Salah satu produk sudah tidak tersedia. Perbarui keranjang lalu coba lagi.")
        subtotal = Decimal("0")
        for product, qty in products:
            if qty < 1 or product.stock < qty:
                raise ValueError(f"Stok {product.name} tidak mencukupi; stok tersedia {product.stock}.")
            subtotal += Decimal(product.price) * qty
        shipping = self.hitung_ongkir(subtotal)
        total = subtotal + shipping
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        order_number = f"AA-{stamp}-{uuid4().hex[:8].upper()}"
        snapshot = address.to_dict()
        order = Order(
            order_number=order_number, user_id=self.customer.id, status="Menunggu pembayaran",
            payment_method=payment_method, subtotal=subtotal, shipping_cost=shipping, total=total,
            recipient_name=address.penerima, recipient_phone=address.telepon,
            shipping_address=address.ringkas, address_snapshot=snapshot,
        )
        db.session.add(order)
        db.session.flush()
        for product, qty in products:
            product.stock -= qty
            order.items.append(OrderItem(
                product_id=product.id, product_name_snapshot=product.name,
                product_image_snapshot=product.gambar, unit_price=product.price, quantity=qty,
            ))
        payment = Payment(method=payment_method, status="Menunggu pembayaran")
        order.payment = payment
        db.session.add(payment)
        if not direct_product_id:
            for row in cart_items_to_remove:
                db.session.delete(row)
        db.session.commit()
        return order
