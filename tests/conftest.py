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


def daftar_dan_login(client, email="pembeli@test.local", nama="Pembeli Uji"):
    client.post("/auth/register", data={
        "email": email, "password": PASSWORD, "konfirmasi_password": PASSWORD, "nama": nama,
        "alamat": "Jl. Contoh No. 1 Batam", "telepon": "081234567890",
    })
    return client.post("/auth/login", data={"email": email, "password": PASSWORD})


def buat_alamat(client):
    r = client.put("/customer/api/addresses", json={
        "daftar": [{"id": "", "label": "Rumah", "penerima": "Pembeli Uji", "telepon": "081234567890", "kodePos": "29461",
                    "provinsi": "Kepulauan Riau", "kota": "Batam", "kecamatan": "Batam Kota", "lengkap": "Jl. Contoh No. 1 Batam"}],
        "utamaId": ""})
    return int(r.get_json()["utamaId"])


def login_admin(client):
    return client.post("/auth/login", data={"email": "admin@albis.local", "password": "PasswordAdminPanjang123"})
