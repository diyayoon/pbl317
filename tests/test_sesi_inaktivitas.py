"""Timeout inaktivitas ditegakkan di server: sebelum batas sah, sesudah batas ditolak dan tidak bisa dihidupkan lagi."""
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import UserSession
from tests.conftest import daftar_dan_login, login_admin

NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


def _geser(app, menit=0, detik=0, email=None, umur_menit=None):
    """Mundurkan waktu aktivitas terakhir (dan opsional umur) semua sesi aktif, seolah waktu berjalan."""
    with app.app_context():
        for rec in UserSession.query.filter(UserSession.revoked_at.is_(None)).all():
            rec.last_activity_at = NOW() - timedelta(minutes=menit, seconds=detik)
            if umur_menit is not None:
                rec.created_at = NOW() - timedelta(minutes=umur_menit)
        db.session.commit()


def _terakhir(app):
    with app.app_context():
        rec = UserSession.query.order_by(UserSession.id.desc()).first()
        t = rec.last_activity_at
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def test_sesi_sah_sebelum_batas_dan_diperpanjang_oleh_aktivitas(app, client):
    daftar_dan_login(client)
    _geser(app, menit=9)
    assert client.get("/customer/api/profile").status_code == 200
    assert NOW() - _terakhir(app) < timedelta(seconds=30)  # aktivitas user memperpanjang


def test_sesi_ditolak_setelah_10_menit_dan_tidak_bisa_hidup_lagi(app, client):
    daftar_dan_login(client)
    _geser(app, menit=10, detik=30)
    r = client.get("/customer/api/profile")
    assert r.status_code == 401 and "tidak ada aktivitas" in r.get_json()["error"]
    # sesi sudah dicabut permanen: tidak bisa "dihidupkan" walau jam dianggap kembali normal
    with app.app_context():
        assert UserSession.query.filter(UserSession.revoked_at.is_(None)).count() == 0
    assert client.get("/customer/api/profile").status_code == 401
    # halaman biasa diarahkan ke login
    assert "/auth/login" in client.get("/customer/pesanan").headers["Location"]


def test_request_latar_belakang_dan_aset_tidak_memperpanjang_sesi(app, client):
    daftar_dan_login(client)
    _geser(app, menit=9)
    sebelum = _terakhir(app)
    assert client.get("/customer/api/cart", headers={"X-Background-Request": "1"}).status_code == 200
    client.get("/static/css/components.css")
    client.get("/health")
    assert abs((_terakhir(app) - sebelum).total_seconds()) < 1  # tidak berubah
    assert client.get("/customer/api/cart").status_code == 200   # aktivitas nyata
    assert NOW() - _terakhir(app) < timedelta(seconds=30)


def test_request_latar_belakang_tetap_ditolak_bila_sudah_lewat_batas(app, client):
    daftar_dan_login(client)
    _geser(app, menit=11)
    assert client.get("/customer/api/cart", headers={"X-Background-Request": "1"}).status_code == 401


def test_cookie_lama_tidak_berlaku_setelah_logout(app, client):
    daftar_dan_login(client)
    cookie = client.get_cookie("albis_session").value
    client.post("/auth/logout")
    penyerang = app.test_client()
    penyerang.set_cookie("albis_session", cookie)
    assert penyerang.get("/customer/api/profile").status_code == 401


def test_admin_lebih_ketat_dari_customer(app):
    adm, cust = app.test_client(), app.test_client()
    login_admin(adm)
    daftar_dan_login(cust)
    _geser(app, menit=6)
    assert adm.get("/admin/api/pesanan").status_code == 401   # admin 5 menit
    assert cust.get("/customer/api/profile").status_code == 200  # customer 10 menit


def test_batas_mutlak_sejak_login_walau_terus_aktif(app, client):
    daftar_dan_login(client)
    _geser(app, menit=0, umur_menit=481)
    assert client.get("/customer/api/profile").status_code == 401


def test_sesi_tanpa_record_server_ditolak(app, client):
    daftar_dan_login(client)
    with app.app_context():
        UserSession.query.delete()
        db.session.commit()
    assert client.get("/customer/api/profile").status_code == 401


def test_remember_me_tidak_membuat_cookie_panjang(client):
    daftar_dan_login(client)
    client.post("/auth/logout")
    r = client.post("/auth/login", data={"email": "pembeli@test.local", "password": "PasswordPanjangBanget123", "remember": "on"})
    assert "remember_token" not in " ".join(r.headers.getlist("Set-Cookie"))


def test_cookie_sesi_httponly_samesite(client):
    r = daftar_dan_login(client)
    cookie = next(c for c in r.headers.getlist("Set-Cookie") if c.startswith("albis_session="))
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_data_bisnis_tetap_ada_setelah_timeout(app, client):
    daftar_dan_login(client)
    client.post("/customer/api/cart", json={"product_id": 1, "quantity": 2})
    _geser(app, menit=15)
    assert client.get("/customer/api/cart").status_code == 401
    client.post("/auth/login", data={"email": "pembeli@test.local", "password": "PasswordPanjangBanget123"})
    items = client.get("/customer/api/cart").get_json()["items"]
    assert len(items) == 1
