"""Pengelolaan akun customer oleh admin."""
from app.extensions import db
from app.models import AuditLog, Order, User
from tests.conftest import PASSWORD, buat_alamat, daftar_dan_login, login_admin


def _siapkan(app, dengan_order=False):
    cust, adm = app.test_client(), app.test_client()
    daftar_dan_login(cust, "cust@test.local", "Customer Uji")
    if dengan_order:
        a = buat_alamat(cust)
        r = cust.post("/customer/api/orders", json={"address_id": a, "payment_method": "Transfer Bank",
                                                    "direct_product_id": 1, "quantity": 1})
        assert r.status_code in (200, 201)
    login_admin(adm)
    with app.app_context():
        uid = User.query.filter_by(email="cust@test.local").one().id
    return cust, adm, uid


def test_admin_melihat_daftar_dan_detail(app):
    _, adm, uid = _siapkan(app)
    daftar = adm.get("/admin/api/pengguna").get_json()
    assert [u["email"] for u in daftar] == ["cust@test.local"]  # admin tidak ikut terdaftar
    assert "password" not in str(daftar).lower()
    d = adm.get(f"/admin/api/pengguna/{uid}").get_json()
    assert d["status"] == "Aktif" and "password_hash" not in d
    assert adm.get("/admin/api/pengguna?q=zzz").get_json() == []


def test_nonaktifkan_mencabut_sesi_dan_login_ditolak_lalu_aktifkan_kembali(app):
    cust, adm, uid = _siapkan(app)
    assert cust.get("/customer/api/profile").status_code == 200
    # alasan wajib
    assert adm.post(f"/admin/api/pengguna/{uid}/status", json={"aksi": "nonaktifkan"}).status_code == 422
    assert adm.post(f"/admin/api/pengguna/{uid}/status", json={"aksi": "nonaktifkan", "alasan": "Email palsu"}).status_code == 200
    assert cust.get("/customer/api/profile").status_code == 401  # sesi yang sedang aktif langsung gugur
    baru = app.test_client()
    baru.post("/auth/login", data={"email": "cust@test.local", "password": PASSWORD})
    assert baru.get("/customer/api/profile").status_code == 401
    assert adm.post(f"/admin/api/pengguna/{uid}/status", json={"aksi": "aktifkan"}).status_code == 200
    baru.post("/auth/login", data={"email": "cust@test.local", "password": PASSWORD})
    assert baru.get("/customer/api/profile").status_code == 200


def test_admin_tidak_bisa_mengelola_admin_atau_id_asal(app):
    _, adm, _ = _siapkan(app)
    with app.app_context():
        admin_id = User.query.filter_by(role="admin").one().id
    assert adm.post(f"/admin/api/pengguna/{admin_id}/status", json={"aksi": "blokir", "alasan": "coba-coba"}).status_code == 404
    assert adm.delete(f"/admin/api/pengguna/{admin_id}", json={"konfirmasi_email": "admin@albis.local"}).status_code == 404
    assert adm.get("/admin/api/pengguna/99999").status_code == 404
    assert adm.post("/admin/api/pengguna/99999/status", json={"aksi": "aktifkan"}).status_code == 404
    with app.app_context():
        assert db.session.get(User, admin_id).is_active is True


def test_customer_tidak_bisa_mengelola_customer_lain(app):
    cust, _, uid = _siapkan(app)
    lain = app.test_client()
    daftar_dan_login(lain, "lain@test.local", "Customer Lain")
    assert lain.post(f"/admin/api/pengguna/{uid}/status", json={"aksi": "blokir", "alasan": "iseng banget"}).status_code == 403
    assert lain.delete(f"/admin/api/pengguna/{uid}", json={"konfirmasi_email": "cust@test.local"}).status_code == 403
    assert cust.get("/customer/api/profile").status_code == 200


def test_hapus_lunak_menjaga_pesanan_dan_menganonimkan(app):
    cust, adm, uid = _siapkan(app, dengan_order=True)
    assert adm.delete(f"/admin/api/pengguna/{uid}", json={"konfirmasi_email": "salah@test.local"}).status_code == 422
    r = adm.delete(f"/admin/api/pengguna/{uid}", json={"konfirmasi_email": "cust@test.local"})
    assert r.status_code == 200 and r.get_json()["status"] == "Dihapus"
    assert cust.get("/customer/api/profile").status_code == 401
    with app.app_context():
        u = db.session.get(User, uid)
        assert u.deleted_at is not None and u.is_active is False
        assert u.email.endswith("@akun.invalid") and u.nama == "Akun Dihapus" and u.telepon == ""
        assert Order.query.filter_by(user_id=uid).count() == 1  # riwayat transaksi utuh
    # email lama bisa dipakai daftar lagi, tapi akun lama tidak bisa login
    baru = app.test_client()
    baru.post("/auth/login", data={"email": "cust@test.local", "password": PASSWORD})
    assert baru.get("/customer/api/profile").status_code == 401
    assert adm.post(f"/admin/api/pengguna/{uid}/status", json={"aksi": "aktifkan"}).status_code == 409


def test_audit_log_tindakan_admin_tanpa_rahasia(app):
    _, adm, uid = _siapkan(app)
    adm.post(f"/admin/api/pengguna/{uid}/status", json={"aksi": "blokir", "alasan": "Penipuan terbukti"})
    with app.app_context():
        baris = AuditLog.query.filter_by(action="akun_blokir").one()
        assert baris.actor_email == "admin@albis.local" and baris.target_id == str(uid)
        for b in AuditLog.query.all():
            assert PASSWORD not in b.detail and "pbkdf2" not in b.detail and "scrypt" not in b.detail
    assert any(a["aksi"] == "akun_blokir" for a in adm.get(f"/admin/api/pengguna/{uid}").get_json()["aktivitas"])
