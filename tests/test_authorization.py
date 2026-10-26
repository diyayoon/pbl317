"""Isolasi data antar-customer dan deny-by-default untuk endpoint admin."""
import io
import re

from app.extensions import db
from app.models import User
from tests.conftest import buat_alamat, daftar_dan_login, login_admin

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _dua_customer(app):
    a, b = app.test_client(), app.test_client()
    daftar_dan_login(a, "a@test.local", "Customer Aaa")
    daftar_dan_login(b, "b@test.local", "Customer Bbb")
    return a, b


def _buat_order(client):
    alamat = buat_alamat(client)
    r = client.post("/customer/api/orders", json={"address_id": alamat, "payment_method": "Transfer Bank",
                                                  "direct_product_id": 1, "quantity": 1})
    assert r.status_code in (200, 201), r.get_json()
    return client.get("/customer/api/orders").get_json()[0]["id"]


def test_cart_tidak_bocor_antar_customer(app):
    a, b = _dua_customer(app)
    assert a.post("/customer/api/cart", json={"product_id": 1, "quantity": 1}).status_code in (200, 201)
    assert len(a.get("/customer/api/cart").get_json()["items"]) == 1
    assert b.get("/customer/api/cart").get_json()["items"] == []
    # B menghapus produk yang sama tidak boleh menyentuh cart A
    b.delete("/customer/api/cart/1")
    assert len(a.get("/customer/api/cart").get_json()["items"]) == 1


def test_pesanan_dan_bukti_bayar_antar_customer(app):
    a, b = _dua_customer(app)
    oid = _buat_order(a)
    assert b.get("/customer/api/orders").get_json() == []
    r = b.post(f"/customer/api/orders/{oid}/bukti", data={"buktiBayar": (io.BytesIO(PNG), "x.png")},
               content_type="multipart/form-data")
    assert r.status_code in (403, 404)
    # pesanan A tetap tanpa bukti
    assert not a.get("/customer/api/orders").get_json()[0].get("buktiBayar")


def test_alamat_customer_lain_tidak_terlihat_dan_tidak_bisa_diubah(app):
    a, b = _dua_customer(app)
    alamat_a = buat_alamat(a)
    assert b.get("/customer/api/addresses").get_json()["daftar"] == []
    # B mencoba menimpa alamat A lewat ID
    b.put("/customer/api/addresses", json={"daftar": [{"id": str(alamat_a), "label": "Hack", "penerima": "Bbb Bbb",
        "telepon": "081234567890", "kodePos": "29461", "provinsi": "Kepri", "kota": "Batam", "kecamatan": "X",
        "lengkap": "Jl. Maling 1"}], "utamaId": ""})
    assert a.get("/customer/api/addresses").get_json()["daftar"][0]["label"] == "Rumah"


def test_manipulasi_payload_profil_tidak_mengubah_role_atau_status(app):
    a, _ = _dua_customer(app)
    a.put("/customer/api/profile", json={"nama": "Customer Aaa", "email": "a@test.local",
                                         "telepon": "081234567890", "role": "admin", "is_active": False,
                                         "is_verified": True})
    with app.app_context():
        u = User.query.filter_by(email="a@test.local").one()
        assert u.role == "customer" and u.is_active is True


def test_semua_endpoint_admin_deny_by_default(app):
    """Setiap rule /admin: anonim ditolak dan customer 403, tanpa mengenal URL atau metode."""
    cust = app.test_client()
    daftar_dan_login(cust, "c@test.local", "Customer Ccc")
    anon = app.test_client()
    aturan = [r for r in app.url_map.iter_rules() if r.rule.startswith("/admin")]
    assert len(aturan) > 20  # jaga-jaga: route admin benar-benar termuat
    for rule in aturan:
        url = re.sub(r"<[^>]+>", "1", rule.rule)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            r_anon = anon.open(url, method=method)
            assert r_anon.status_code in (302, 401, 403), (method, url, r_anon.status_code)
            r_cust = cust.open(url, method=method)
            assert r_cust.status_code == 403, (method, url, r_cust.status_code)


def test_admin_tidak_bisa_pakai_endpoint_customer(app):
    adm = app.test_client()
    login_admin(adm)
    for url in ("/customer/api/cart", "/customer/api/orders", "/customer/api/profile"):
        assert adm.get(url).status_code == 403, url


def test_csrf_menolak_perubahan_admin_tanpa_token():
    """Config test mematikan CSRF; di sini dinyalakan untuk membuktikan endpoint mutasi terlindungi."""
    from app import buat_app
    from app.config import TestingConfig

    class CsrfConfig(TestingConfig):
        WTF_CSRF_ENABLED = True

    app = buat_app(CsrfConfig)
    with app.app_context():
        db.create_all()
        adm = User(email="admin2@albis.local", nama="Admin Dua", role="admin", telepon="")
        adm.set_password("PasswordAdminPanjang123")
        cust = User(email="korban@test.local", nama="Korban Uji", role="customer", telepon="")
        cust.set_password("PasswordPanjangBanget123")
        db.session.add_all([adm, cust])
        db.session.commit()
        uid = cust.id
    try:
        c = app.test_client()
        page = c.get("/auth/login").get_data(as_text=True)
        token = re.search(r'name="csrf-token" content="([^"]+)"', page) or re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page)
        assert token, "token CSRF tidak ditemukan di halaman login"
        c.post("/auth/login", data={"email": "admin2@albis.local", "password": "PasswordAdminPanjang123", "csrf_token": token.group(1)})
        url = f"/admin/api/pengguna/{uid}/status"
        body = {"aksi": "blokir", "alasan": "uji csrf"}
        assert c.post(url, json=body).status_code == 400            # tanpa token ditolak
        halaman = c.get("/admin/pengguna").get_data(as_text=True)
        t2 = re.search(r'name="csrf-token" content="([^"]+)"', halaman).group(1)
        assert c.post(url, json=body, headers={"X-CSRFToken": t2}).status_code == 200  # dengan token diterima
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()
