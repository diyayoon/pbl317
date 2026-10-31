from __future__ import annotations
import re
from sqlalchemy import select
from app.extensions import db
from app.models import Address, Cart, CartItem, Product, User


class LayananPelanggan:
    @staticmethod
    def ambil_keranjang(user: User, buat=True) -> Cart | None:
        cart = Cart.query.filter_by(user_id=user.id).first()
        if cart is None and buat:
            cart = Cart(user_id=user.id)
            db.session.add(cart)
            db.session.commit()
        return cart

    @classmethod
    def daftar_keranjang(cls, user: User) -> list[dict]:
        cart = cls.ambil_keranjang(user)
        return [item.to_dict() for item in cart.items if item.product and item.product.is_active] if cart else []

    @classmethod
    def tambah_keranjang(cls, user: User, product_id: int, quantity: int = 1):
        if quantity < 1 or quantity > 100:
            raise ValueError("Jumlah produk harus antara 1 dan 100.")
        product = db.session.scalar(select(Product).where(Product.id == product_id, Product.is_active.is_(True)).with_for_update())
        if product is None:
            raise LookupError("Produk tidak ditemukan.")
        if product.stock < 1:
            raise ValueError("Stok produk sedang habis.")
        cart = cls.ambil_keranjang(user)
        item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
        new_quantity = quantity + (item.quantity if item else 0)
        if new_quantity > product.stock:
            raise ValueError(f"Stok tersedia hanya {product.stock} item.")
        if item:
            item.quantity = new_quantity
            item.selected = True
        else:
            item = CartItem(cart=cart, product=product, quantity=quantity, selected=True)
            db.session.add(item)
        db.session.commit()
        return item.to_dict()

    @classmethod
    def ubah_keranjang(cls, user: User, product_id: int, quantity: int | None = None, selected: bool | None = None):
        cart = cls.ambil_keranjang(user)
        item = CartItem.query.join(Cart).filter(Cart.user_id == user.id, CartItem.product_id == product_id).first()
        if not cart or not item:
            raise LookupError("Item tidak ditemukan di keranjang.")
        if quantity is not None:
            if quantity <= 0:
                db.session.delete(item)
                db.session.commit()
                return None
            if quantity > item.product.stock:
                raise ValueError(f"Stok tersedia hanya {item.product.stock} item.")
            item.quantity = quantity
        if selected is not None:
            item.selected = bool(selected)
        db.session.commit()
        return item.to_dict()

    @classmethod
    def pilih_semua(cls, user: User, selected: bool):
        cart = cls.ambil_keranjang(user)
        if cart:
            for item in cart.items:
                item.selected = bool(selected)
            db.session.commit()
        return cls.daftar_keranjang(user)

    @classmethod
    def hapus_keranjang(cls, user: User, product_id: int | None = None, selected_only=False):
        cart = cls.ambil_keranjang(user)
        if not cart:
            return
        for item in list(cart.items):
            if product_id is not None and item.product_id != product_id:
                continue
            if selected_only and not item.selected:
                continue
            db.session.delete(item)
        db.session.commit()

    @staticmethod
    def daftar_alamat(user: User) -> dict:
        addresses = Address.query.filter_by(user_id=user.id).order_by(Address.id.asc()).all()
        primary = next((address for address in addresses if address.is_primary), addresses[0] if addresses else None)
        return {"daftar": [address.to_dict() for address in addresses], "utamaId": str(primary.id) if primary else None}

    @classmethod
    def simpan_daftar_alamat(cls, user: User, payload: dict) -> dict:
        raw_list = payload.get("daftar") if isinstance(payload, dict) else None
        main_id = str(payload.get("utamaId") or "") if isinstance(payload, dict) else ""
        if not isinstance(raw_list, list) or len(raw_list) > 30:
            raise ValueError("Daftar alamat tidak valid atau terlalu banyak.")
        existing = {str(address.id): address for address in Address.query.filter_by(user_id=user.id).all()}
        keep_ids: set[int] = set()
        desired_primary: int | None = None
        for raw in raw_list:
            if not isinstance(raw, dict):
                raise ValueError("Format alamat tidak valid.")
            fields = {
                "label": str(raw.get("label") or "Alamat").strip()[:30],
                "penerima": str(raw.get("penerima") or "").strip(),
                "telepon": str(raw.get("telepon") or "").strip(),
                "kode_pos": str(raw.get("kodePos") or "").strip(),
                "provinsi": str(raw.get("provinsi") or "").strip(),
                "kota": str(raw.get("kota") or "").strip(),
                "kecamatan": str(raw.get("kecamatan") or "").strip(),
                "lengkap": str(raw.get("lengkap") or "").strip(),
            }
            if not all(fields[key] for key in ("penerima", "telepon", "kode_pos", "provinsi", "kota", "kecamatan", "lengkap")):
                raise ValueError("Semua detail alamat wajib lengkap sebelum disimpan.")
            if any(len(fields[key]) > 100 for key in ("penerima", "provinsi", "kota", "kecamatan")) or len(fields["lengkap"]) > 255:
                raise ValueError("Salah satu kolom alamat terlalu panjang.")
            digits = re.sub(r"[^\d+]", "", fields["telepon"]).replace("+", "")
            digits = "62" + digits[1:] if digits.startswith("0") else digits
            if not re.fullmatch(r"62\d{8,13}", digits):
                raise ValueError("Nomor telepon penerima harus diawali 62 dan berisi 10–15 angka.")
            fields["telepon"] = digits
            if len(fields["lengkap"]) < 10 or not (len(fields["kode_pos"]) == 5 and fields["kode_pos"].isdigit()):
                raise ValueError("Alamat lengkap minimal 10 karakter dan kode pos harus 5 angka.")
            old_id = str(raw.get("id") or "")
            address = existing.get(old_id) if old_id.isdigit() else None
            if address is None:
                address = Address(user_id=user.id)
                db.session.add(address)
            for key, value in fields.items():
                setattr(address, key, value)
            db.session.flush()
            keep_ids.add(address.id)
            if old_id == main_id:
                desired_primary = address.id
        for address in existing.values():
            if address.id not in keep_ids:
                db.session.delete(address)
        db.session.flush()
        remaining = Address.query.filter_by(user_id=user.id).all()
        if desired_primary is None and remaining:
            desired_primary = remaining[0].id
        for address in remaining:
            address.is_primary = address.id == desired_primary
        db.session.commit()
        return cls.daftar_alamat(user)

    @classmethod
    def update_profile(
        cls,
        user: User,
        payload: dict,
        avatar_path: str | None = None,
        remove_avatar: bool = False,
    ):
        if not isinstance(payload, dict):
            raise ValueError("Data profil tidak valid.")
        if "foto" in payload:
            raise ValueError("Foto profil harus dikirim sebagai berkas, bukan data teks.")

        name = str(payload.get("nama") or "").strip()
        email = str(payload.get("email") or "").strip().lower()
        phone = str(payload.get("telepon") or "").strip()

        if len(name) < 3 or len(name) > 100 or not re.fullmatch(r"[^\W\d_][\w .'-]*", name, flags=re.UNICODE):
            raise ValueError("Nama harus terdiri dari 3–100 karakter yang valid.")
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Format email tidak valid.")
        if email != user.email:
            raise ValueError("Email login tidak dapat diubah dari halaman profil.")

        digits = re.sub(r"[^\d+]", "", phone).replace("+", "")
        if digits.startswith("0"):
            digits = "62" + digits[1:]
        if phone and not re.fullmatch(r"62\d{8,13}", digits):
            raise ValueError("Nomor telepon harus diawali 62 dan berisi 10–15 angka.")
        if not phone:
            digits = ""

        if avatar_path is not None and not re.fullmatch(
            r"/media/avatars/[0-9a-f]{32}\.(?:jpg|jpeg|png|webp)", avatar_path
        ):
            raise ValueError("Lokasi foto profil tidak valid.")

        user.nama = name
        user.email = email
        user.telepon = digits
        if avatar_path is not None:
            user.avatar_data = avatar_path
        elif remove_avatar:
            user.avatar_data = None

        db.session.commit()
        return {
            "nama": user.nama,
            "email": user.email,
            "telepon": user.telepon,
            "foto": user.avatar_data,
        }
