"""Pengajuan refund customer, keputusan admin, dan konfirmasi Midtrans."""
from app.extensions import db
from app.models import Order, Product, RefundRequest
from tests.conftest import buat_alamat, daftar_dan_login, login_admin


def _order_lunas(client, app, midtrans_ready):
    daftar_dan_login(client)
    address_id = buat_alamat(client)
    response = client.post("/customer/api/orders", json={
        "address_id": address_id, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1,
    })
    assert response.status_code == 201
    order = response.get_json()["order"]
    with app.app_context():
        row = db.session.get(Order, order["id"])
        row.status = "Diproses"
        row.payment.status = "Disetujui"
        row.payment.gateway_status = "settlement"
        row.payment.gateway_payment_type = "qris"
        row.payment.gateway_transaction_id = "transaction-test"
        db.session.commit()
    return order


def test_customer_dapat_mengajukan_refund_dan_admin_melihat_readonly(app, client, midtrans_ready, monkeypatch):
    order = _order_lunas(client, app, midtrans_ready)
    from app.services import midtrans_service as ms
    monkeypatch.setattr(ms, "_http", lambda method, url, body=None: (200, {
        "status_code": "200", "order_id": order["orderNumber"], "gross_amount": f"{order['total']}.00",
        "transaction_status": "settlement", "payment_type": "qris", "transaction_id": "transaction-test",
    }))
    response = client.post(f"/customer/api/orders/{order['id']}/refund", json={"alasan": "Barang tidak sesuai deskripsi."})
    assert response.status_code == 201
    with app.app_context():
        request_row = RefundRequest.query.one()
        assert request_row.status == "Menunggu persetujuan"
        assert request_row.amount == order["total"]
        refund_id = request_row.id
    admin = app.test_client()
    assert login_admin(admin).status_code == 302
    listing = admin.get("/admin/api/refund").get_json()
    assert listing[0]["id"] == refund_id
    assert listing[0]["status"] == "Menunggu persetujuan"


def test_admin_reject_refund_tidak_mengubah_pesanan_dan_pembayaran(app, client, midtrans_ready, monkeypatch):
    order = _order_lunas(client, app, midtrans_ready)
    from app.services import midtrans_service as ms
    monkeypatch.setattr(ms, "_http", lambda method, url, body=None: (200, {
        "status_code": "200", "gross_amount": f"{order['total']}.00", "transaction_status": "settlement", "payment_type": "qris",
    }))
    assert client.post(f"/customer/api/orders/{order['id']}/refund", json={"alasan": "Saya berubah pikiran."}).status_code == 201
    admin = app.test_client(); login_admin(admin)
    with app.app_context():
        refund_id = RefundRequest.query.one().id
    response = admin.post(f"/admin/api/refund/{refund_id}/tinjau", json={"aksi": "tolak", "catatan": "Alasan tidak memenuhi kebijakan toko."})
    assert response.status_code == 200
    with app.app_context():
        row = db.session.get(Order, order["id"])
        assert row.status == "Diproses" and row.payment.status == "Disetujui"
        assert db.session.get(RefundRequest, refund_id).status == "Ditolak"


def test_admin_approve_refund_then_sync_confirms_and_returns_stock(app, client, midtrans_ready, monkeypatch):
    order = _order_lunas(client, app, midtrans_ready)
    from app.services import midtrans_service as ms
    state = {"approved": False, "refund_body": None}

    def fake_http(method, url, body=None):
        if method == "GET" and url.endswith("/status"):
            base = {"status_code": "200", "order_id": order["orderNumber"], "gross_amount": f"{order['total']}.00",
                    "transaction_id": "transaction-test", "payment_type": "qris"}
            if state["approved"]:
                base.update({"transaction_status": "refund", "refunds": [{
                    "refund_key": state["refund_body"]["refund_key"], "refund_amount": str(order["total"]),
                    "bank_confirmed_at": "2026-11-05 00:00:00",
                }]})
            else:
                base["transaction_status"] = "settlement"
            return 200, base
        if method == "POST" and url.endswith("/refund"):
            state["approved"] = True; state["refund_body"] = body
            return 200, {"status_code": "200", "transaction_status": "refund", "refund_chargeback_id": "refund-123"}
        raise AssertionError((method, url))

    monkeypatch.setattr(ms, "_http", fake_http)
    assert client.post(f"/customer/api/orders/{order['id']}/refund", json={"alasan": "Barang tidak sesuai deskripsi."}).status_code == 201
    admin = app.test_client(); login_admin(admin)
    with app.app_context():
        refund_id = RefundRequest.query.one().id
        stock_before = db.session.get(Product, 1).stock
    approved = admin.post(f"/admin/api/refund/{refund_id}/tinjau", json={"aksi": "setujui", "catatan": "Disetujui setelah pemeriksaan."})
    assert approved.status_code == 200 and approved.get_json()["refund"]["status"] == "Diproses"
    synced = admin.post(f"/admin/api/refund/{refund_id}/sinkron", json={})
    assert synced.status_code == 200 and synced.get_json()["refund"]["status"] == "Berhasil"
    with app.app_context():
        row = db.session.get(Order, order["id"])
        assert row.status == "Direfund" and row.payment.status == "Direfund"
        assert db.session.get(Product, 1).stock == stock_before + 1


def test_customer_hanya_bisa_refund_pesanan_miliknya_sendiri(client, app, midtrans_ready):
    order = _order_lunas(client, app, midtrans_ready)
    other = app.test_client()
    daftar_dan_login(other, email="other@test.local", nama="Pembeli Lain")
    response = other.post(f"/customer/api/orders/{order['id']}/refund", json={"alasan": "Barang tidak sesuai deskripsi."})
    assert response.status_code == 404


def test_customer_tidak_bisa_refund_metode_transfer_bank(app, client, midtrans_ready, monkeypatch):
    order = _order_lunas(client, app, midtrans_ready)
    from app.services import midtrans_service as ms
    monkeypatch.setattr(ms, "_http", lambda method, url, body=None: (200, {
        "status_code": "200", "gross_amount": f"{order['total']}.00", "transaction_status": "settlement", "payment_type": "bank_transfer",
    }))
    response = client.post(f"/customer/api/orders/{order['id']}/refund", json={"alasan": "Barang tidak sesuai deskripsi."})
    assert response.status_code == 409


def test_pesanan_tidak_bisa_dikirim_selama_refund_menunggu_persetujuan(app, client, midtrans_ready, monkeypatch):
    order = _order_lunas(client, app, midtrans_ready)
    from app.services import midtrans_service as ms
    monkeypatch.setattr(ms, "_http", lambda method, url, body=None: (200, {
        "status_code": "200", "gross_amount": f"{order['total']}.00",
        "transaction_status": "settlement", "payment_type": "qris",
    }))
    assert client.post(f"/customer/api/orders/{order['id']}/refund", json={"alasan": "Barang tidak sesuai deskripsi."}).status_code == 201
    admin = app.test_client(); login_admin(admin)
    response = admin.patch(f"/admin/api/pesanan/{order['id']}", json={"status": "Dikirim"})
    assert response.status_code == 422
    assert "refund" in response.get_json()["error"].lower()


def test_refund_partial_dari_gateway_tidak_menandai_pesanan_direfund(app, client, midtrans_ready, monkeypatch):
    order = _order_lunas(client, app, midtrans_ready)
    from app.services import midtrans_service as ms
    state = {"refund_key": None}

    def fake_http(method, url, body=None):
        if method == "GET" and url.endswith("/status"):
            if state["refund_key"]:
                return 200, {"status_code": "200", "gross_amount": f"{order['total']}.00",
                             "transaction_status": "partial_refund", "payment_type": "qris",
                             "refunds": [{"refund_key": state["refund_key"], "refund_amount": "500000.00",
                                          "bank_confirmed_at": "2026-11-05 00:00:00"}]}
            return 200, {"status_code": "200", "gross_amount": f"{order['total']}.00",
                         "transaction_status": "settlement", "payment_type": "qris"}
        if method == "POST" and url.endswith("/refund"):
            state["refund_key"] = body["refund_key"]
            return 200, {"status_code": "200", "transaction_status": "partial_refund"}
        raise AssertionError((method, url))

    monkeypatch.setattr(ms, "_http", fake_http)
    assert client.post(f"/customer/api/orders/{order['id']}/refund", json={"alasan": "Barang tidak sesuai deskripsi."}).status_code == 201
    admin = app.test_client(); login_admin(admin)
    with app.app_context():
        refund_id = RefundRequest.query.one().id
    assert admin.post(f"/admin/api/refund/{refund_id}/tinjau", json={"aksi": "setujui"}).status_code == 200
    response = admin.post(f"/admin/api/refund/{refund_id}/sinkron", json={})
    assert response.status_code == 200
    assert response.get_json()["refund"]["status"] == "Diproses"
    with app.app_context():
        row = db.session.get(Order, order["id"])
        assert row.status == "Diproses" and row.payment.status == "Disetujui"
