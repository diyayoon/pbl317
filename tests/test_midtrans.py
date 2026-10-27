"""Integrasi Midtrans (Snap Redirect). Jaringan di-mock: ini BUKAN bukti uji end-to-end ke sandbox Midtrans."""
import hashlib
import io
import json

import pytest

from app.extensions import db
from app.models import Order, Product, User
from app.services import midtrans_service as ms
from tests.conftest import buat_alamat, daftar_dan_login, login_admin

KUNCI = "SB-Mid-server-KUNCIUJI1234567890"
URL_BAYAR = "https://app.sandbox.midtrans.com/snap/v4/redirection/abc-123"


class FakeMidtrans:
    """Pengganti ms._http: merekam panggilan dan mengembalikan jawaban yang bisa diatur test."""
    def __init__(self):
        self.panggilan, self.status_resp, self.snap_resp, self.mati = [], {}, (201, {"token": "t", "redirect_url": URL_BAYAR}), False

    def __call__(self, metode, url, body=None):
        if self.mati:
            raise ms.ErrorMidtrans("Layanan pembayaran sedang tidak dapat dihubungi.", 503)
        self.panggilan.append((metode, url, body))
        return self.snap_resp if metode == "POST" else (200, self.status_resp)


@pytest.fixture()
def mid(app, monkeypatch):
    app.config.update(MIDTRANS_SERVER_KEY=KUNCI, MIDTRANS_IS_PRODUCTION=False, APP_BASE_URL="http://localhost:5000")
    palsu = FakeMidtrans()
    monkeypatch.setattr(ms, "_http", palsu)
    return palsu


def _pesan(client, metode="Midtrans"):
    a = buat_alamat(client)
    r = client.post("/customer/api/orders", json={"address_id": a, "payment_method": metode, "direct_product_id": 1, "quantity": 1})
    assert r.status_code in (200, 201), r.get_json()
    return client.get("/customer/api/orders").get_json()[0]


def _ttd(data):
    bahan = f"{data['order_id']}{data['status_code']}{data['gross_amount']}{KUNCI}"
    return hashlib.sha512(bahan.encode()).hexdigest()


def _notif(order, status="settlement", fraud="accept", gross=None, salah=False):
    data = {"order_id": order["orderNumber"], "status_code": "200", "gross_amount": gross or f"{order['total']}.00",
            "transaction_status": status, "fraud_status": fraud, "payment_type": "bank_transfer", "transaction_id": "tx-1"}
    data["signature_key"] = "0" * 128 if salah else _ttd(data)
    return data


def _kirim_notif(client, mid, order, **kw):
    data = _notif(order, **kw)
    mid.status_resp = {k: v for k, v in data.items() if k != "signature_key"}   # status resmi dari Midtrans
    return client.post("/midtrans/notifikasi", json=data)


def _keadaan(app, order_id):
    with app.app_context():
        o = db.session.get(Order, order_id)
        return o.status, o.payment.status, db.session.get(Product, 1).stock


def test_metode_midtrans_hanya_ada_bila_dikonfigurasi(app, client):
    daftar_dan_login(client)
    a = buat_alamat(client)
    r = client.post("/customer/api/orders", json={"address_id": a, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1})
    assert r.status_code in (400, 422)                                   # kunci kosong -> ditolak
    html = client.get("/customer/checkout").get_data(as_text=True)
    assert "Bayar Online (Midtrans)" in html and 'data-midtrans-ready="false" disabled' in html
    app.config["MIDTRANS_SERVER_KEY"] = KUNCI
    html = client.get("/customer/checkout").get_data(as_text=True)
    assert "Bayar Online (Midtrans)" in html and 'data-midtrans-ready="true"' in html



def test_checkout_membuat_pesanan_dan_langsung_memberi_url_snap(client, mid):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    r = client.post("/customer/api/orders", json={"address_id": alamat, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1})
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["redirectUrl"] == URL_BAYAR
    assert payload["order"]["status"] == "Menunggu pembayaran"
    assert len(mid.panggilan) == 1 and mid.panggilan[0][0] == "POST"

def test_buat_transaksi_mengirim_data_benar_dan_dipakai_ulang(client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    r = client.post(f"/customer/api/orders/{order['id']}/midtrans")
    assert r.status_code == 200 and r.get_json()["redirectUrl"] == URL_BAYAR
    metode, url, body = mid.panggilan[0]
    assert (metode, url) == ("POST", "https://app.sandbox.midtrans.com/snap/v1/transactions")
    assert body["transaction_details"] == {"order_id": order["orderNumber"], "gross_amount": order["total"]}
    assert body["callbacks"]["finish"].startswith("http://localhost:5000/customer/pesanan")
    assert KUNCI not in json.dumps(body) and KUNCI not in r.get_data(as_text=True)
    client.post(f"/customer/api/orders/{order['id']}/midtrans")
    assert len(mid.panggilan) == 1                                       # transaksi tidak dibuat dua kali


def test_hanya_pemilik_terverifikasi_yang_bisa_bayar(app, client, mid):
    daftar_dan_login(client, "a@mid.local", "Pemilik Satu")
    order = _pesan(client)
    lain = app.test_client(); daftar_dan_login(lain, "b@mid.local", "Pemilik Dua")
    assert lain.post(f"/customer/api/orders/{order['id']}/midtrans").status_code == 404           # IDOR
    assert lain.post(f"/customer/api/orders/{order['id']}/midtrans/sinkron").status_code == 404
    anon, adm = app.test_client(), app.test_client(); login_admin(adm)
    assert anon.post(f"/customer/api/orders/{order['id']}/midtrans").status_code in (302, 401)
    assert adm.post(f"/customer/api/orders/{order['id']}/midtrans").status_code == 403
    belum = app.test_client(); daftar_dan_login(belum, "c@mid.local", "Belum Verifikasi", verifikasi=False)
    assert belum.post("/customer/api/orders/1/midtrans").status_code == 403
    assert len(mid.panggilan) == 1  # hanya transaksi pemilik; upaya lintas akun tidak memanggil Midtrans


def test_checkout_hanya_menerima_midtrans_dan_menolak_bukti_manual(client, mid):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    transfer = client.post("/customer/api/orders", json={"address_id": alamat, "payment_method": "Transfer Bank", "direct_product_id": 1, "quantity": 1})
    assert transfer.status_code == 422
    online = _pesan(client)
    r = client.post(f"/customer/api/orders/{online['id']}/bukti", data={"buktiBayar": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 50), "x.png")},
                    content_type="multipart/form-data")
    assert r.status_code in (400, 409, 422)


def test_gagal_membuat_transaksi_memberi_error_dan_order_pending_bisa_dicoba_lagi(client, mid):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    mid.snap_resp = (401, {"error_messages": ["Access denied"]})
    dibuat = client.post("/customer/api/orders", json={"address_id": alamat, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1})
    assert dibuat.status_code == 502
    order_id = dibuat.get_json()["orderId"]
    assert order_id is not None
    with client.application.app_context():
        order = Order.query.filter_by(id=order_id).one()
        assert order.status == "Menunggu pembayaran" and not order.payment.snap_redirect_url
    mid.mati = True
    assert client.post(f"/customer/api/orders/{order_id}/midtrans").status_code == 503
    assert client.get("/customer/api/orders").get_json()[0]["status"] == "Menunggu pembayaran"


def test_notifikasi_signature_salah_ditolak(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    pub = app.test_client()
    assert _kirim_notif(pub, mid, order, salah=True).status_code == 403
    assert pub.post("/midtrans/notifikasi", data="bukan json").status_code == 400
    assert _keadaan(app, order["id"])[:2] == ("Menunggu pembayaran", "Menunggu pembayaran")


def test_notifikasi_settlement_melunasi_idempoten_dan_tidak_diturunkan(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    pub = app.test_client()
    assert _kirim_notif(pub, mid, order).status_code == 200
    assert _keadaan(app, order["id"])[:2] == ("Diproses", "Disetujui")
    assert _kirim_notif(pub, mid, order).status_code == 200                  # kirim ulang: aman
    assert _kirim_notif(pub, mid, order, status="pending").status_code == 200  # notifikasi pending terlambat
    assert _keadaan(app, order["id"])[:2] == ("Diproses", "Disetujui")
    with app.app_context():
        p = Order.query.get(order["id"]).payment
        assert p.gateway_payment_type == "bank_transfer" and p.paid_at is not None


def test_capture_hanya_lunas_bila_fraud_accept(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    pub = app.test_client()
    _kirim_notif(pub, mid, order, status="capture", fraud="challenge")
    assert _keadaan(app, order["id"])[0] == "Menunggu pembayaran"
    _kirim_notif(pub, mid, order, status="capture", fraud="accept")
    assert _keadaan(app, order["id"])[0] == "Diproses"


def test_jumlah_tidak_cocok_ditolak_dan_pesanan_tetap(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    r = _kirim_notif(app.test_client(), mid, order, gross="1000.00")
    assert r.status_code == 400 and _keadaan(app, order["id"])[0] == "Menunggu pembayaran"


def test_order_tidak_dikenal_dan_midtrans_mati_membuat_retry(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    pub = app.test_client()
    hantu = dict(order, orderNumber="AA-TIDAK-ADA")
    assert _kirim_notif(pub, mid, hantu).status_code == 404
    mid.mati = True
    assert pub.post("/midtrans/notifikasi", json=_notif(order)).status_code == 503   # 5xx: Midtrans akan mengulang
    assert _keadaan(app, order["id"])[0] == "Menunggu pembayaran"


def test_notifikasi_tanpa_token_csrf_tetap_diterima_saat_csrf_aktif(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    app.config["WTF_CSRF_ENABLED"] = True
    assert _kirim_notif(app.test_client(), mid, order).status_code == 200


def test_expire_membatalkan_pesanan_dan_mengembalikan_stok(app, client, mid):
    daftar_dan_login(client)
    with app.app_context():
        awal = db.session.get(Product, 1).stock
    order = _pesan(client)
    assert _keadaan(app, order["id"])[2] == awal - 1
    _kirim_notif(app.test_client(), mid, order, status="expire")
    assert _keadaan(app, order["id"]) == ("Dibatalkan", "Kedaluwarsa", awal)


def test_bayar_setelah_pesanan_dibatalkan_ditandai_untuk_admin(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    pub = app.test_client()
    _kirim_notif(pub, mid, order, status="expire")
    _kirim_notif(pub, mid, order, status="settlement")
    status, bayar, _ = _keadaan(app, order["id"])
    assert status == "Dibatalkan"                                            # tidak dihidupkan paksa (stok sudah dilepas)
    with app.app_context():
        assert "perlu penanganan admin" in Order.query.get(order["id"]).payment.review_note


def test_sinkron_setelah_kembali_dari_midtrans_tanpa_webhook(app, client, mid):
    daftar_dan_login(client)
    order = _pesan(client)
    client.post(f"/customer/api/orders/{order['id']}/midtrans")
    mid.status_resp = {k: v for k, v in _notif(order).items() if k != "signature_key"}
    r = client.post(f"/customer/api/orders/{order['id']}/midtrans/sinkron")
    assert r.status_code == 200 and r.get_json()["status"] == "Diproses"
    assert mid.panggilan[-1][:2] == ("GET", f"https://api.sandbox.midtrans.com/v2/{order['orderNumber']}/status")


def test_pesanan_lunas_midtrans_bisa_dikirim_admin(app, client, mid):
    from app.services.order_service import LayananPesanan
    daftar_dan_login(client)
    order = _pesan(client)
    _kirim_notif(app.test_client(), mid, order)
    with app.app_context():
        admin = User.query.filter_by(role="admin").first() or User(email="adm@x.local", nama="Adm", role="admin")
        if admin.id is None:
            admin.set_password("PasswordAdminPanjang123"); db.session.add(admin); db.session.commit()
        LayananPesanan.ubah_status(Order.query.get(order["id"]), "Dikirim", admin)
        assert Order.query.get(order["id"]).status == "Dikirim"


def test_server_key_tidak_bocor_ke_log_saat_gagal(client, mid, caplog):
    daftar_dan_login(client)
    order = _pesan(client)
    mid.snap_resp = (500, {})
    client.post(f"/customer/api/orders/{order['id']}/midtrans")
    assert KUNCI not in caplog.text


def test_kunci_tanpa_awalan_sb_tetap_diterima_di_produksi_mode_sandbox(app):
    """Regresi: kunci sandbox tidak selalu berawalan SB-; jangan menolak start hanya karena awalan."""
    from app import _validasi_konfigurasi
    app.config.update(TESTING=False, APP_ENV="production", SECRET_KEY="k" * 40, APP_BASE_URL="https://toko.example",
                      SQLALCHEMY_DATABASE_URI="postgresql+psycopg://u:p@h/db", MIDTRANS_IS_PRODUCTION=False,
                      MIDTRANS_SERVER_KEY="Mid-server-tanpaAwalanSB")
    _validasi_konfigurasi(app)
    app.config["TESTING"] = True


def test_perintah_uji_midtrans_melaporkan_hasil_tanpa_membocorkan_kunci(app, monkeypatch):
    runner = app.test_cli_runner()
    app.config.update(MIDTRANS_SERVER_KEY="", MIDTRANS_IS_PRODUCTION=False)
    assert "belum diisi" in runner.invoke(args=["uji-midtrans"]).output
    app.config["MIDTRANS_SERVER_KEY"] = KUNCI
    monkeypatch.setattr(ms, "_http", lambda m, u, b=None: (201, {"redirect_url": URL_BAYAR}))
    r = runner.invoke(args=["uji-midtrans"])
    assert "BERHASIL" in r.output and KUNCI not in r.output
    monkeypatch.setattr(ms, "_http", lambda m, u, b=None: (401, {"error_messages": ["Access denied"]}))
    r = runner.invoke(args=["uji-midtrans"])
    assert r.exit_code == 1 and "DITOLAK (401)" in r.output and KUNCI not in r.output
    app.config["MIDTRANS_IS_PRODUCTION"] = True
    assert "hanya untuk sandbox" in runner.invoke(args=["uji-midtrans"]).output


def test_notifikasi_tanpa_content_length_tetap_diproses(app, client, mid):
    """Pengiriman chunked tidak membawa Content-Length; jangan ditolak (Midtrans akan mengulang tanpa henti)."""
    daftar_dan_login(client)
    order = _pesan(client)
    data = _notif(order)
    mid.status_resp = {k: v for k, v in data.items() if k != "signature_key"}
    r = app.test_client().post("/midtrans/notifikasi", data=json.dumps(data), content_type="application/json",
                               environ_overrides={"CONTENT_LENGTH": "", "HTTP_TRANSFER_ENCODING": "chunked", "wsgi.input_terminated": True})
    assert r.status_code == 200 and _keadaan(app, order["id"])[:2] == ("Diproses", "Disetujui")


def test_notifikasi_terlalu_besar_ditolak(app, client, mid):
    app.config["MIDTRANS_SERVER_KEY"] = KUNCI
    besar = {"order_id": "X", "padding": "a" * 25000}
    assert app.test_client().post("/midtrans/notifikasi", json=besar).status_code == 400
