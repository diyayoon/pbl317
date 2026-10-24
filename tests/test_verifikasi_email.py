"""Verifikasi email: token hash, kedaluwarsa, sekali pakai, resend dibatasi, aksi sensitif diblokir."""
import re
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models import AuditLog, EmailVerificationToken, User
from tests.conftest import PASSWORD, buat_alamat, daftar_dan_login


@pytest.fixture()
def surat(monkeypatch):
    """Tangkap email keluar (SMTP asli tidak dipanggil)."""
    kotak = []
    monkeypatch.setattr("app.utils.email.kirim_email", lambda tujuan, subjek, isi: kotak.append((tujuan, subjek, isi)) or True)
    return kotak


def _token(surat_item):
    return re.search(r"/auth/verifikasi/([\w-]+)", surat_item[2]).group(1)


def _daftar(client, email="baru@test.local"):
    return daftar_dan_login(client, email, "Pengguna Baru", verifikasi=False)


def _order(client):
    a = buat_alamat(client)
    return client.post("/customer/api/orders", json={"address_id": a, "payment_method": "Transfer Bank",
                                                     "direct_product_id": 1, "quantity": 1})


def test_registrasi_mengirim_email_dan_akun_belum_terverifikasi(client, app, surat):
    _daftar(client)
    assert len(surat) == 1 and surat[0][0] == "baru@test.local"
    with app.app_context():
        assert User.query.filter_by(email="baru@test.local").one().is_verified is False


def test_token_disimpan_sebagai_hash_dan_tidak_masuk_audit(client, app, surat):
    _daftar(client)
    raw = _token(surat[0])
    with app.app_context():
        t = EmailVerificationToken.query.one()
        assert t.token_hash != raw and raw not in t.token_hash and len(t.token_hash) == 64
        assert all(raw not in (a.detail or "") for a in AuditLog.query.all())


def test_akun_belum_verifikasi_bisa_login_tapi_tidak_bisa_pesan_bayar_ulas(client, surat):
    _daftar(client)
    assert client.get("/customer/api/profile").status_code == 200
    r = _order(client)
    assert r.status_code == 403 and r.get_json()["perluVerifikasi"] is True
    import io
    assert client.post("/customer/api/orders/1/bukti", data={"buktiBayar": (io.BytesIO(b"x"), "x.png")},
                       content_type="multipart/form-data").status_code == 403
    assert client.post("/customer/api/reviews", json={"product_id": 1, "rating": 5, "komentar": "bagus"}).status_code == 403


def test_get_tautan_tidak_memverifikasi_post_memverifikasi_dan_sekali_pakai(client, app, surat):
    _daftar(client)
    raw = _token(surat[0])
    assert client.get(f"/auth/verifikasi/{raw}").status_code == 200  # hanya halaman konfirmasi
    with app.app_context():
        assert User.query.filter_by(email="baru@test.local").one().is_verified is False
    assert client.post(f"/auth/verifikasi/{raw}").status_code == 200
    assert _order(client).status_code == 201  # setelah verifikasi, checkout terbuka
    assert client.post(f"/auth/verifikasi/{raw}").status_code == 400  # token tidak bisa dipakai ulang


def test_token_kedaluwarsa_dan_token_ngawur_ditolak(client, app, surat):
    _daftar(client)
    raw = _token(surat[0])
    with app.app_context():
        t = EmailVerificationToken.query.one()
        t.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
    assert client.post(f"/auth/verifikasi/{raw}").status_code == 400
    assert client.post("/auth/verifikasi/token-ngawur").status_code == 400
    assert client.post(f"/auth/verifikasi/{raw[:-2]}xx").status_code == 400
    with app.app_context():
        assert User.query.filter_by(email="baru@test.local").one().is_verified is False


def test_kirim_ulang_dibatasi_dan_membatalkan_token_lama(client, app, surat):
    _daftar(client)
    lama = _token(surat[0])
    r = client.post("/auth/verifikasi/kirim-ulang", follow_redirects=True)
    assert len(surat) == 1 and "Tunggu" in r.get_data(as_text=True)  # cooldown aktif
    app.config["EMAIL_VERIFY_COOLDOWN_DETIK"] = 0
    client.post("/auth/verifikasi/kirim-ulang")
    assert len(surat) == 2
    baru = _token(surat[1])
    assert client.post(f"/auth/verifikasi/{lama}").status_code == 400  # tautan lama gugur
    assert client.post(f"/auth/verifikasi/{baru}").status_code == 200


def test_kirim_ulang_batas_per_jam(client, app, surat):
    app.config["EMAIL_VERIFY_COOLDOWN_DETIK"] = 0
    app.config["EMAIL_VERIFY_MAX_PER_JAM"] = 3
    _daftar(client)  # 1 email dari registrasi (tidak dihitung kuota resend)
    for _ in range(6):
        client.post("/auth/verifikasi/kirim-ulang")
    assert len(surat) == 1 + 3


def test_kirim_ulang_butuh_login(client, surat):
    assert client.post("/auth/verifikasi/kirim-ulang").status_code in (302, 401)
    assert surat == []


def test_akun_nonaktif_tidak_bisa_diverifikasi(client, app, surat):
    _daftar(client)
    raw = _token(surat[0])
    with app.app_context():
        User.query.filter_by(email="baru@test.local").update({"is_active": False})
        db.session.commit()
    assert client.post(f"/auth/verifikasi/{raw}").status_code == 400


def test_registrasi_tetap_berhasil_tanpa_smtp(client, app):
    """Tanpa MAIL_* tidak ada pengiriman palsu: akun dibuat, tetap belum terverifikasi."""
    r = client.post("/auth/register", data={"email": "nosmtp@test.local", "password": PASSWORD, "konfirmasi_password": PASSWORD,
                                            "nama": "Tanpa Smtp", "alamat": "Jl. Contoh No. 1 Batam", "telepon": "081234567890"},
                    follow_redirects=True)
    assert "belum terkirim" in r.get_data(as_text=True)
    with app.app_context():
        assert User.query.filter_by(email="nosmtp@test.local").one().is_verified is False


def test_pengirim_smtp_memakai_starttls_login_dan_tidak_membocorkan_password(app, monkeypatch, caplog):
    from app.utils import email as mailer
    app.config.update(MAIL_SERVER="smtp.example.com", MAIL_PORT=587, MAIL_SECURITY="starttls",
                      MAIL_USERNAME="toko@example.com", MAIL_PASSWORD="RahasiaAppPassword", MAIL_FROM="toko@example.com")
    jejak = []

    class SMTPPalsu:
        def __init__(self, host, port, timeout=None): jejak.append(("connect", host, port))
        def starttls(self, context=None): jejak.append(("starttls",))
        def login(self, u, p): jejak.append(("login", u, p))
        def send_message(self, m): jejak.append(("kirim", m["To"]))
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr("smtplib.SMTP", SMTPPalsu)
    with app.test_request_context():
        assert mailer.kirim_email("a@test.local", "Subjek", "Isi") is True
    assert [j[0] for j in jejak] == ["connect", "starttls", "login", "kirim"]
    assert "RahasiaAppPassword" not in caplog.text


# ---------- kode OTP lewat email + halaman verifikasi ----------
def _kode(item):
    return re.search(r"Kode verifikasi: (\d+)", item[2]).group(1)


def _salah(kode):
    return "".join(str((int(c) + 1) % 10) for c in kode)


def _daftar_tanpa_login(client, email="otp@test.local"):
    return client.post("/auth/register", data={"email": email, "password": PASSWORD, "konfirmasi_password": PASSWORD,
                                               "nama": "Pengguna Otp", "alamat": "Jl. Contoh No. 1 Batam", "telepon": "081234567890"})


def test_registrasi_mengarah_ke_halaman_cek_email_dengan_email_tersamar(client, surat):
    r = _daftar_tanpa_login(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/auth/verifikasi/cek-email")
    html = client.get("/auth/verifikasi/cek-email").get_data(as_text=True)
    assert "o**" in html and "otp@test.local" not in html          # email tidak ditampilkan utuh
    assert "Kembali ke login" in html and "Kirim ulang" in html and "Masukkan kode" in html
    assert re.fullmatch(r"\d{6}", _kode(surat[0])) and "/auth/verifikasi/" in surat[0][2]  # email berisi kode dan tautan


def test_halaman_kode_menampilkan_input_dan_hitung_mundur(client, surat):
    _daftar_tanpa_login(client)
    html = client.get("/auth/verifikasi/kode").get_data(as_text=True)
    assert 'maxlength="6"' in html and 'autocomplete="one-time-code"' in html and 'id="tombolLanjut"' in html
    sisa = int(re.search(r'data-sisa="(\d+)"', html).group(1))
    assert 0 < sisa <= 60                                              # cooldown kirim ulang berjalan


def test_kode_benar_memverifikasi_tanpa_login_lalu_bisa_belanja(client, app, surat):
    _daftar_tanpa_login(client)
    r = client.post("/auth/verifikasi/kode", data={"kode": _kode(surat[0])})
    assert r.status_code == 302 and r.headers["Location"].endswith("/auth/login")
    with app.app_context():
        assert User.query.filter_by(email="otp@test.local").one().is_verified is True
    client.post("/auth/login", data={"email": "otp@test.local", "password": PASSWORD})
    assert _order(client).status_code == 201
    assert client.post("/auth/verifikasi/kode", data={"kode": _kode(surat[0])}).status_code == 302  # sudah verified: tidak error


def test_kode_salah_dibatasi_lalu_mati_dan_perlu_kirim_ulang(client, app, surat):
    app.config["EMAIL_VERIFY_COOLDOWN_DETIK"] = 0
    _daftar_tanpa_login(client)
    asli = _kode(surat[0])
    for i in range(4):
        assert client.post("/auth/verifikasi/kode", data={"kode": _salah(asli)}).status_code == 422
    assert client.post("/auth/verifikasi/kode", data={"kode": _salah(asli)}).status_code == 400   # percobaan ke-5: kode dimatikan
    assert client.post("/auth/verifikasi/kode", data={"kode": asli}).status_code == 400            # kode benar pun ditolak
    with app.app_context():
        assert User.query.filter_by(email="otp@test.local").one().is_verified is False
    client.post("/auth/verifikasi/kirim-ulang")
    baru = _kode(surat[1])
    assert client.post("/auth/verifikasi/kode", data={"kode": baru}).status_code == 302


def test_kirim_ulang_membuat_kode_lama_tidak_berlaku(client, app, surat):
    app.config["EMAIL_VERIFY_COOLDOWN_DETIK"] = 0
    _daftar_tanpa_login(client)
    client.post("/auth/verifikasi/kirim-ulang")
    lama, baru = _kode(surat[0]), _kode(surat[1])
    if lama != baru:  # (peluang kembar 1 banding sejuta)
        assert client.post("/auth/verifikasi/kode", data={"kode": lama}).status_code == 422
    assert client.post("/auth/verifikasi/kode", data={"kode": baru}).status_code == 302


def test_kode_kedaluwarsa_ditolak(client, app, surat):
    _daftar_tanpa_login(client)
    with app.app_context():
        t = EmailVerificationToken.query.one()
        t.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
    assert client.post("/auth/verifikasi/kode", data={"kode": _kode(surat[0])}).status_code == 400


def test_kode_akun_lain_tidak_bisa_dipakai(app, surat):
    a, b = app.test_client(), app.test_client()
    _daftar_tanpa_login(a, "a-otp@test.local")
    _daftar_tanpa_login(b, "b-otp@test.local")
    assert b.post("/auth/verifikasi/kode", data={"kode": _kode(surat[0])}).status_code in (400, 422)  # kode milik A
    with app.app_context():
        assert User.query.filter_by(email="a-otp@test.local").one().is_verified is False
        assert User.query.filter_by(email="b-otp@test.local").one().is_verified is False


def test_kode_disimpan_hash_dan_tidak_masuk_audit(client, app, surat):
    _daftar_tanpa_login(client)
    kode = _kode(surat[0])
    client.post("/auth/verifikasi/kode", data={"kode": _salah(kode)})
    with app.app_context():
        t = EmailVerificationToken.query.one()
        assert t.code_hash and kode not in t.code_hash and len(t.code_hash) == 64
        assert all(kode not in (a.detail or "") and _salah(kode) not in (a.detail or "") for a in AuditLog.query.all())


def test_format_kode_tidak_valid_tidak_menghabiskan_percobaan(client, app, surat):
    _daftar_tanpa_login(client)
    for jelek in ("", "abc123", "12345", "1234567", "12 3", "١٢٣٤٥٦"):
        assert client.post("/auth/verifikasi/kode", data={"kode": jelek}).status_code == 422
    with app.app_context():
        assert EmailVerificationToken.query.one().attempts == 0


def test_panjang_kode_bisa_diatur(client, app, surat):
    app.config["EMAIL_VERIFY_KODE_DIGIT"] = 4
    _daftar_tanpa_login(client)
    assert re.fullmatch(r"\d{4}", _kode(surat[0]))
    assert 'maxlength="4"' in client.get("/auth/verifikasi/kode").get_data(as_text=True)


def test_halaman_verifikasi_butuh_akun_yang_sedang_didaftarkan(client, surat):
    for url in ("/auth/verifikasi/kode", "/auth/verifikasi/cek-email"):
        assert client.get(url).status_code == 302 and "/auth/login" in client.get(url).headers["Location"]
    assert client.post("/auth/verifikasi/kode", data={"kode": "123456"}).status_code == 302
    assert surat == []


def test_user_login_belum_verifikasi_memakai_halaman_kode_dan_masuk_dashboard(client, surat):
    _daftar(client)
    assert client.get("/auth/verifikasi").headers["Location"].endswith("/auth/verifikasi/kode")
    r = client.post("/auth/verifikasi/kode", data={"kode": _kode(surat[0])})
    assert r.status_code == 302 and "/customer" in r.headers["Location"]


def test_samarkan_email():
    from app.services.verifikasi_email_service import samarkan_email
    assert samarkan_email("mahdiya2017@gmail.com") == "m********17@gmail.com"
    assert samarkan_email("ab@x.id").endswith("@x.id") and "ab@" not in samarkan_email("ab@x.id")


def test_produksi_wajib_app_base_url_dan_tautan_tidak_memakai_header_host(app, client, surat):
    from app import _validasi_konfigurasi
    app.config.update(TESTING=False, APP_ENV="production", SECRET_KEY="k" * 40,
                      SQLALCHEMY_DATABASE_URI="postgresql+psycopg://u:p@h/db", APP_BASE_URL="")
    with pytest.raises(RuntimeError, match="APP_BASE_URL"):
        _validasi_konfigurasi(app)
    app.config["APP_BASE_URL"] = "https://toko.example"
    _validasi_konfigurasi(app)                       # lengkap: tidak error
    app.config["TESTING"] = True                     # kembalikan agar request biasa jalan
    client.post("/auth/register", data={"email": "host@test.local", "password": PASSWORD, "konfirmasi_password": PASSWORD,
                                        "nama": "Uji Host", "alamat": "Jl. Contoh No. 1 Batam", "telepon": "081234567890"},
                headers={"Host": "evil.example"})
    assert "https://toko.example/auth/verifikasi/" in surat[0][2] and "evil.example" not in surat[0][2]
