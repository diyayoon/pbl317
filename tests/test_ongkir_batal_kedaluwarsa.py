"""Ongkir server-side, pembatalan oleh pelanggan, dan kedaluwarsa pesanan berkala."""
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models import Order, Product
from app.services import midtrans_service as ms
from tests.conftest import buat_alamat, daftar_dan_login, login_admin


def _pesan(client, metode="Transfer Bank", qty=1):
    a = buat_alamat(client)
    r = client.post("/customer/api/orders", json={"address_id": a, "payment_method": metode, "direct_product_id": 1, "quantity": qty})
    assert r.status_code in (200, 201), r.get_json()
    return r.get_json()["order"]


def _stok(app):
    with app.app_context():
        return db.session.get(Product, 1).stock


# ---------------- ongkir ----------------
def test_ongkir_masuk_total_dan_data_checkout(app, client):
    daftar_dan_login(client)
    data = client.get("/customer/api/checkout?direct_product_id=1&quantity=1").get_json()
    assert data["ongkir"] == 25_000
    o = _pesan(client)
    with app.app_context():
        row = db.session.get(Order, o["id"])
        assert int(row.shipping_cost) == 25_000 and int(row.total) == int(row.subtotal) + 25_000
    assert client.get("/customer/api/orders").get_json()[0]["ongkir"] == 25_000


def test_gratis_ongkir_di_atas_ambang_dan_ongkir_nol(app, client):
    daftar_dan_login(client)
    app.config["SHIPPING_FREE_ABOVE"] = 1_000_000
    assert _pesan(client, qty=2)["total"] == 2_000_000          # subtotal 2 jt >= ambang: gratis
    app.config.update(SHIPPING_FREE_ABOVE=0, SHIPPING_COST_FLAT=0)
    assert client.get("/customer/api/checkout?direct_product_id=1&quantity=1").get_json()["ongkir"] == 0


def test_klien_tidak_bisa_menentukan_ongkir(app, client):
    daftar_dan_login(client)
    a = buat_alamat(client)
    r = client.post("/customer/api/orders", json={"address_id": a, "payment_method": "Transfer Bank", "direct_product_id": 1,
                                                  "quantity": 1, "shipping_cost": 0, "ongkir": 0, "total": 1})
    assert r.get_json()["order"]["total"] == 1_000_000 + 25_000


def test_midtrans_menagih_total_termasuk_ongkir(app, client, monkeypatch):
    app.config.update(MIDTRANS_SERVER_KEY="SB-Mid-server-x", APP_BASE_URL="http://localhost:5000")
    kirim = []
    monkeypatch.setattr(ms, "_http", lambda m, u, b=None: kirim.append(b) or (201, {"redirect_url": "https://app.sandbox.midtrans.com/snap/v4/redirection/x"}))
    daftar_dan_login(client)
    o = _pesan(client, "Midtrans")
    client.post(f"/customer/api/orders/{o['id']}/midtrans")
    assert kirim[0]["transaction_details"]["gross_amount"] == 1_025_000


# ---------------- pembatalan oleh pelanggan ----------------
def test_pelanggan_membatalkan_pesanan_sendiri_dan_stok_kembali(app, client):
    daftar_dan_login(client)
    awal = _stok(app)
    o = _pesan(client)
    assert _stok(app) == awal - 1
    r = client.post(f"/customer/api/orders/{o['id']}/batal")
    assert r.status_code == 200 and r.get_json()["status"] == "Dibatalkan"
    assert _stok(app) == awal
    with app.app_context():
        row = db.session.get(Order, o["id"])
        assert row.status == "Dibatalkan" and row.payment.status == "Dibatalkan"
    assert client.post(f"/customer/api/orders/{o['id']}/batal").status_code == 409     # tidak bisa dua kali
    assert _stok(app) == awal                                                          # stok tidak bertambah ganda


def test_batal_membuka_kembali_kuota_pesanan_terbuka(app, client):
    daftar_dan_login(client)
    app.config["MAX_OPEN_ORDERS"] = 1
    o = _pesan(client)
    a = buat_alamat(client)
    bayar = {"address_id": a, "payment_method": "Transfer Bank", "direct_product_id": 1, "quantity": 1}
    assert client.post("/customer/api/orders", json=bayar).status_code == 422          # kuota penuh
    client.post(f"/customer/api/orders/{o['id']}/batal")
    assert client.post("/customer/api/orders", json=bayar).status_code in (200, 201)


def test_pembatalan_milik_orang_lain_dan_akses_tanpa_hak_ditolak(app, client):
    daftar_dan_login(client, "a@batal.local", "Pemilik Satu")
    o = _pesan(client)
    lain = app.test_client(); daftar_dan_login(lain, "b@batal.local", "Pemilik Dua")
    assert lain.post(f"/customer/api/orders/{o['id']}/batal").status_code == 404          # IDOR
    anon, adm = app.test_client(), app.test_client(); login_admin(adm)
    assert anon.post(f"/customer/api/orders/{o['id']}/batal").status_code in (302, 401)
    assert adm.post(f"/customer/api/orders/{o['id']}/batal").status_code == 403
    with app.app_context():
        assert db.session.get(Order, o["id"]).status == "Menunggu pembayaran"


@pytest.mark.parametrize("status", ["Menunggu persetujuan", "Diproses", "Dikirim", "Selesai"])
def test_pesanan_yang_sudah_diajukan_atau_dibayar_tidak_bisa_dibatalkan_sendiri(app, client, status):
    daftar_dan_login(client)
    o = _pesan(client)
    with app.app_context():
        db.session.get(Order, o["id"]).status = status
        db.session.commit()
    assert client.post(f"/customer/api/orders/{o['id']}/batal").status_code == 409


class _Midtrans:
    def __init__(self): self.panggilan, self.status, self.mati = [], {}, False
    def __call__(self, metode, url, body=None):
        if self.mati: raise ms.ErrorMidtrans("Layanan pembayaran sedang tidak dapat dihubungi.", 503)
        self.panggilan.append((metode, url))
        return (200, self.status)


@pytest.fixture()
def mid(app, monkeypatch):
    app.config.update(MIDTRANS_SERVER_KEY="SB-Mid-server-x", APP_BASE_URL="http://localhost:5000")
    palsu = _Midtrans()
    monkeypatch.setattr(ms, "_http", palsu)
    return palsu


def _pesan_midtrans_dengan_transaksi(app, client, mid):
    daftar_dan_login(client)
    o = _pesan(client, "Midtrans")
    with app.app_context():
        db.session.get(Order, o["id"]).payment.snap_redirect_url = "https://app.sandbox.midtrans.com/snap/v4/redirection/x"
        db.session.commit()
    return o


def test_batal_pesanan_midtrans_ikut_membatalkan_di_midtrans(app, client, mid):
    o = _pesan_midtrans_dengan_transaksi(app, client, mid)
    mid.status = {"order_id": o["orderNumber"], "gross_amount": f"{o['total']}.00", "transaction_status": "pending"}
    assert client.post(f"/customer/api/orders/{o['id']}/batal").status_code == 200
    assert ("POST", f"https://api.sandbox.midtrans.com/v2/{o['orderNumber']}/cancel") in mid.panggilan


def test_batal_ditolak_bila_ternyata_sudah_dibayar_di_midtrans(app, client, mid):
    o = _pesan_midtrans_dengan_transaksi(app, client, mid)
    mid.status = {"order_id": o["orderNumber"], "gross_amount": f"{o['total']}.00", "transaction_status": "settlement",
                  "payment_type": "bank_transfer", "transaction_id": "t1"}
    r = client.post(f"/customer/api/orders/{o['id']}/batal")
    assert r.status_code == 409
    with app.app_context():
        assert db.session.get(Order, o["id"]).status == "Diproses"          # tersinkron lunas, bukan dibatalkan


def test_batal_pesanan_midtrans_ditolak_bila_midtrans_tidak_terjangkau(app, client, mid):
    o = _pesan_midtrans_dengan_transaksi(app, client, mid)
    mid.mati = True
    assert client.post(f"/customer/api/orders/{o['id']}/batal").status_code == 503
    with app.app_context():
        assert db.session.get(Order, o["id"]).status == "Menunggu pembayaran"   # tidak dibatalkan sembarangan


# ---------------- kedaluwarsa berkala ----------------
def _usangkan(app, order_id, jam=25):
    with app.app_context():
        db.session.get(Order, order_id).created_at = datetime.now(timezone.utc) - timedelta(hours=jam)
        db.session.commit()


def test_kedaluwarsa_berjalan_sendiri_saat_halaman_dibuka(app, client):
    from app import kedaluwarsa
    daftar_dan_login(client)
    awal = _stok(app)
    o = _pesan(client)
    _usangkan(app, o["id"])
    app.config["ORDER_EXPIRE_INTERVAL_DETIK"] = 60
    kedaluwarsa._terakhir = None
    assert app.test_client().get("/katalog").status_code == 200       # pengunjung anonim membuka katalog
    with app.app_context():
        row = db.session.get(Order, o["id"])
        assert row.status == "Dibatalkan" and row.payment.status == "Kedaluwarsa"
    assert _stok(app) == awal                                          # stok kembali tanpa menunggu checkout orang lain


def test_kedaluwarsa_dibatasi_interval_dan_tidak_menyentuh_pesanan_baru(app, client):
    from app import kedaluwarsa
    daftar_dan_login(client)
    o = _pesan(client)
    app.config["ORDER_EXPIRE_INTERVAL_DETIK"] = 3600
    kedaluwarsa._terakhir = None
    app.test_client().get("/katalog")                                  # menjalankan sekali; pesanan baru tidak disentuh
    with app.app_context():
        assert db.session.get(Order, o["id"]).status == "Menunggu pembayaran"
    _usangkan(app, o["id"])
    app.test_client().get("/katalog")                                  # masih dalam interval: belum dijalankan lagi
    with app.app_context():
        assert db.session.get(Order, o["id"]).status == "Menunggu pembayaran"


def test_kegagalan_kedaluwarsa_tidak_merusak_halaman(app, client, monkeypatch):
    from app import kedaluwarsa
    from app.services.order_service import LayananPesanan
    def rusak(cls): raise RuntimeError("db mati")
    monkeypatch.setattr(LayananPesanan, "kedaluwarsakan", classmethod(rusak))
    app.config["ORDER_EXPIRE_INTERVAL_DETIK"] = 60
    kedaluwarsa._terakhir = None
    assert client.get("/katalog").status_code == 200


def test_kedaluwarsa_jalan_walau_mesin_baru_menyala(app, client, monkeypatch):
    """Regresi: jangan bergantung pada nilai time.monotonic (uptime mesin yang kecil membuat hook tidak jalan)."""
    from app import kedaluwarsa
    daftar_dan_login(client)
    o = _pesan(client)
    _usangkan(app, o["id"])
    monkeypatch.setattr(kedaluwarsa.time, "monotonic", lambda: 5.0)     # mesin baru menyala 5 detik
    app.config["ORDER_EXPIRE_INTERVAL_DETIK"] = 60
    kedaluwarsa._terakhir = None
    app.test_client().get("/katalog")
    with app.app_context():
        assert db.session.get(Order, o["id"]).status == "Dibatalkan"
