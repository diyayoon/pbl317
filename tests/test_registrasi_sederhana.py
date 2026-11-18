"""Registrasi 4 kolom, profil dilengkapi setelah login, dan ganti password mandiri."""
import re

from app.extensions import db
from app.models import User
from tests.conftest import PASSWORD, daftar_dan_login

BARU = "PasswordBaruYangPanjang456"


def _daftar(client, **tambahan):
    data = {"email": "empat@test.local", "nama": "Empat Kolom", "password": PASSWORD, "konfirmasi_password": PASSWORD}
    data.update(tambahan)
    return client.post("/auth/register", data=data)


def test_form_register_hanya_empat_kolom(client):
    html = client.get("/auth/register").get_data(as_text=True)
    kolom = set(re.findall(r'<(?:input|textarea)[^>]*name="([a-z_]+)"', html)) - {"csrf_token"}
    assert kolom == {"email", "nama", "password", "konfirmasi_password"}


def test_daftar_tanpa_alamat_dan_telepon_berhasil_lalu_cek_email(client, app):
    r = _daftar(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/auth/verifikasi/cek-email")
    with app.app_context():
        u = User.query.filter_by(email="empat@test.local").one()
        assert u.telepon == "" and u.alamat_registrasi is None and u.is_verified is False


def test_alamat_telepon_kiriman_lama_diabaikan_dan_role_tidak_bisa_diubah(client, app):
    _daftar(client, alamat="Jl. Palsu 99", telepon="081234567890", role="admin", is_verified="1")
    with app.app_context():
        u = User.query.filter_by(email="empat@test.local").one()
        assert u.telepon == "" and u.alamat_registrasi is None and u.role == "customer" and u.is_verified is False


def test_validasi_tetap_menolak_password_tidak_cocok_dan_nama_kosong(client):
    assert _daftar(client, konfirmasi_password="beda").status_code == 422
    assert _daftar(client, nama="").status_code == 422
    assert _daftar(client, password="pendek", konfirmasi_password="pendek").status_code == 422


def test_profil_telepon_opsional_lalu_bisa_diisi_setelah_login(app):
    c = app.test_client()
    daftar_dan_login(c, "profil@test.local", "Profil Uji")
    with app.app_context():
        User.query.filter_by(email="profil@test.local").update({"telepon": ""})
        db.session.commit()
    dasar = {"nama": "Profil Uji", "email": "profil@test.local"}
    assert c.put("/customer/api/profile", json={**dasar, "telepon": ""}).status_code == 200      # boleh kosong
    assert c.put("/customer/api/profile", json={**dasar, "telepon": "abc"}).status_code in (400, 422)
    assert c.put("/customer/api/profile", json={**dasar, "telepon": "081234567890"}).status_code == 200
    assert c.get("/customer/api/profile").get_json()["telepon"] == "6281234567890"


def test_ganti_password_mandiri_end_to_end(app):
    a = app.test_client()
    daftar_dan_login(a, "ganti@test.local", "Ganti Sandi")
    assert a.get("/customer/keamanan").status_code == 200
    # password lama salah / baru lemah / konfirmasi beda -> ditolak, password tidak berubah
    for data in ({"password_lama": "salah", "password_baru": BARU, "konfirmasi_password": BARU},
                 {"password_lama": PASSWORD, "password_baru": "pendek", "konfirmasi_password": "pendek"},
                 {"password_lama": PASSWORD, "password_baru": BARU, "konfirmasi_password": "beda"}):
        a.post("/customer/keamanan", data=data)
    b = app.test_client()
    assert b.post("/auth/login", data={"email": "ganti@test.local", "password": PASSWORD}).status_code == 302
    # berhasil
    r = a.post("/customer/keamanan", data={"password_lama": PASSWORD, "password_baru": BARU, "konfirmasi_password": BARU})
    assert r.status_code == 302
    assert a.get("/customer/api/profile").status_code == 200       # sesi yang mengganti tetap hidup
    assert b.get("/customer/api/profile").status_code == 401       # sesi perangkat lain dicabut
    c = app.test_client()
    c.post("/auth/login", data={"email": "ganti@test.local", "password": PASSWORD})
    assert c.get("/customer/api/profile").status_code == 401       # password lama tidak berlaku
    c.post("/auth/login", data={"email": "ganti@test.local", "password": BARU})
    assert c.get("/customer/api/profile").status_code == 200       # password baru berlaku
