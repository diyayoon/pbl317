from app.models import AuditLog, User
from tests.conftest import PASSWORD, daftar_dan_login, login_admin


def test_header_keamanan_dan_cookie(client):
    r = client.get("/")
    csp = r.headers["Content-Security-Policy"]
    assert "script-src 'self';" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in r.headers


def test_halaman_error_tidak_membocorkan_detail(client):
    r = client.get("/produk/9999")
    assert r.status_code == 404 and b"Traceback" not in r.data


def test_register_selalu_customer_walau_payload_role_admin(client, app):
    client.post("/auth/register", data={"email": "x@test.local", "password": PASSWORD, "konfirmasi_password": PASSWORD,
                                        "nama": "Orang Biasa", "alamat": "Jl. Contoh No. 1", "telepon": "081234567890", "role": "admin"})
    with app.app_context():
        assert User.query.filter_by(email="x@test.local").one().role == "customer"


def test_password_disimpan_sebagai_hash(client, app):
    daftar_dan_login(client)
    with app.app_context():
        user = User.query.filter_by(email="pembeli@test.local").one()
        assert user.password_hash != PASSWORD and user.password_hash.startswith(("scrypt:", "pbkdf2:"))


def test_lockout_setelah_lima_login_gagal(client):
    daftar_dan_login(client)
    client.post("/auth/logout")
    for _ in range(5):
        assert client.post("/auth/login", data={"email": "pembeli@test.local", "password": "salah-salah-salah"}).status_code == 401
    assert client.post("/auth/login", data={"email": "pembeli@test.local", "password": PASSWORD}).status_code == 429


def test_next_tidak_boleh_keluar_situs(client):
    daftar_dan_login(client)
    client.post("/auth/logout")
    for evil in ("//evil.example", "https://evil.example", "/%5Cevil.example", "/\\evil.example"):
        r = client.post(f"/auth/login?next={evil}", data={"email": "pembeli@test.local", "password": PASSWORD})
        assert r.status_code == 302
        assert "evil.example" not in r.headers["Location"].replace("%5C", "") or r.headers["Location"].startswith("/%5C")
        assert not r.headers["Location"].startswith("//")
        client.post("/auth/logout")


def test_api_tanpa_login_401_json(client):
    r = client.get("/customer/api/cart")
    assert r.status_code == 401 and r.get_json()["error"]


def test_customer_tidak_bisa_akses_admin(client):
    daftar_dan_login(client)
    assert client.get("/admin/").status_code == 403
    assert client.post("/admin/api/produk", json={}).status_code == 403
    assert client.get("/admin/api/pembayaran").status_code == 403


def test_logout_hanya_post(client):
    assert client.get("/auth/logout").status_code == 405


def test_ganti_password_mencabut_sesi_lain(app):
    a, b = app.test_client(), app.test_client()
    daftar_dan_login(a)
    b.post("/auth/login", data={"email": "pembeli@test.local", "password": PASSWORD})
    assert b.get("/customer/akun").status_code == 200
    r = a.post("/customer/keamanan", data={"password_lama": PASSWORD, "password_baru": "PasswordBaruSuperPanjang1", "konfirmasi_password": "PasswordBaruSuperPanjang1"})
    assert r.status_code == 302
    assert b.get("/customer/akun").status_code == 302       # sesi lama dicabut
    assert a.get("/customer/akun").status_code == 200       # sesi yang mengganti tetap hidup


def test_audit_log_mencatat_login(client, app):
    daftar_dan_login(client)
    with app.app_context():
        aksi = {row.action for row in AuditLog.query.all()}
        assert {"registrasi", "login_berhasil"} <= aksi


def test_audit_log_tidak_menyimpan_password(client, app):
    client.post("/auth/login", data={"email": "pembeli@test.local", "password": "RahasiaBanget123456"})
    with app.app_context():
        assert all("RahasiaBanget" not in (row.detail + row.actor_email) for row in AuditLog.query.all())


def test_admin_login_dan_halaman(client):
    assert login_admin(client).status_code == 302
    for path in ("/admin/", "/admin/produk", "/admin/kategori", "/admin/pesanan", "/admin/pembayaran", "/admin/ulasan", "/admin/laporan", "/admin/audit", "/admin/akun"):
        assert client.get(path).status_code == 200, path


def test_login_admin_dicatat_dengan_aksi_khusus(client, app):
    assert login_admin(client).status_code == 302
    with app.app_context():
        assert AuditLog.query.filter_by(action="login_admin_berhasil", actor_email="admin@albis.local").count() == 1


def test_pembuatan_admin_hanya_melalui_command_cli(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-admin", "--email", "operator@test.local", "--nama", "Operator Uji"],
                           input="PasswordAdminUjiPanjang123!\nPasswordAdminUjiPanjang123!\n")
    assert result.exit_code == 0, result.output
    with app.app_context():
        user = User.query.filter_by(email="operator@test.local").one()
        assert user.role == "admin" and user.is_verified is True
