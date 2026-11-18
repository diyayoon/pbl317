import pytest

from app import buat_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Category, Product, ProductImage, User

PASSWORD = "PasswordPanjangBanget123"


@pytest.fixture()
def app():
    app = buat_app(TestingConfig)
    # Konteks aplikasi TIDAK dibiarkan terbuka saat request, supaya g/_login_user tidak bocor antar klien.
    with app.app_context():
        db.create_all()
        kategori = Category(name="Jam & Timepiece", slug="timepiece", icon="◷")
        db.session.add(kategori)
        db.session.flush()
        produk = Product(category=kategori, name="Jam Saku Uji", slug="jam-saku-uji", description="Jam saku antik untuk pengujian.",
                         price=1000000, stock=3, era="1900", origin="Swiss", material="Kuningan", condition="Good",
                         authenticity_status="Verified", image_alt="Jam")
        produk.images.append(ProductImage(image_url="https://example.com/jam.jpg", alt_text="Jam", is_primary=True, position=0))
        db.session.add(produk)
        admin = User(email="admin@albis.local", nama="Admin Uji", role="admin", telepon="")
        admin.set_password("PasswordAdminPanjang123")
        db.session.add(admin)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def daftar_dan_login(client, email="pembeli@test.local", nama="Pembeli Uji", verifikasi=True):
    client.post("/auth/register", data={
        "email": email, "password": PASSWORD, "konfirmasi_password": PASSWORD, "nama": nama,
        "alamat": "Jl. Contoh No. 1 Batam", "telepon": "081234567890",
    })
    if verifikasi:  # alur lama (sebelum ada verifikasi email) mengasumsikan akun langsung bisa belanja
        with client.application.app_context():
            User.query.filter_by(email=email).update({"is_verified": True})
            db.session.commit()
    return client.post("/auth/login", data={"email": email, "password": PASSWORD})


def buat_alamat(client):
    r = client.put("/customer/api/addresses", json={
        "daftar": [{"id": "", "label": "Rumah", "penerima": "Pembeli Uji", "telepon": "081234567890", "kodePos": "29461",
                    "provinsi": "Kepulauan Riau", "kota": "Batam", "kecamatan": "Batam Kota", "lengkap": "Jl. Contoh No. 1 Batam"}],
        "utamaId": ""})
    return int(r.get_json()["utamaId"])


def login_admin(client):
    return client.post("/auth/login", data={"email": "admin@albis.local", "password": "PasswordAdminPanjang123"})


@pytest.fixture()
def midtrans_ready(app, monkeypatch):
    """Midtrans sandbox lokal palsu untuk tes alur; tidak melakukan panggilan jaringan."""
    from app.services import midtrans_service as ms

    app.config.update(
        MIDTRANS_SERVER_KEY="SB-Mid-server-UNIT-TEST-ONLY",
        MIDTRANS_IS_PRODUCTION=False,
        APP_BASE_URL="http://localhost:5000",
    )
    transaksi = {}

    def fake_http(method, url, body=None):
        if url.endswith("/cancel"):
            return 200, {"status_code": "200"}
        if method == "POST" and "/snap/v1/transactions" in url:
            detail = (body or {}).get("transaction_details", {})
            order_id = str(detail.get("order_id") or "")
            total = int(detail.get("gross_amount") or 0)
            transaksi[order_id] = total
            return 201, {"token": "test-token", "redirect_url": f"https://app.sandbox.midtrans.com/snap/v4/redirection/{order_id}"}
        if method == "GET" and "/status" in url:
            order_id = url.rstrip("/").split("/")[-2]
            if order_id not in transaksi:
                return 404, {"status_code": "404"}
            return 200, {
                "order_id": order_id,
                "status_code": "200",
                "gross_amount": f"{transaksi[order_id]}.00",
                "transaction_status": "pending",
                "payment_type": "qris",
                "transaction_id": f"test-{order_id}",
            }
        return 200, {"status_code": "200"}

    monkeypatch.setattr(ms, "_http", fake_http)
    return transaksi
