"""Regression tests for Application Audit Trail and Wazuh JSONL events."""
import json

from app.extensions import db
from app.models import AuditLog, User
from tests.conftest import buat_alamat, daftar_dan_login, login_admin


def test_audit_jsonl_hanya_ditulis_setelah_commit(app, client, tmp_path):
    target = tmp_path / "logs" / "albis_audit.jsonl"
    app.config["AUDIT_LOG_FILE"] = str(target)

    daftar_dan_login(client, email="jsonl@test.local", nama="JSONL Test")

    assert target.exists()
    events = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    event = next(item for item in events if item["event_action"] == "auth.register.success")
    assert event["app"] == "albis-antique"
    assert event["event_id"]
    assert event["request_id"]
    assert event["event_category"] == "authentication"
    assert event["actor_role"] == "customer"
    assert "password" not in json.dumps(event).lower()
    assert "jsonl@test.local" not in json.dumps(event)


def test_login_gagal_menghasilkan_event_normalisasi_tanpa_email_mentah(client, app):
    client.post("/auth/login", data={"email": "rahasia@example.test", "password": "PasswordYangSalah123"})
    with app.app_context():
        row = AuditLog.query.filter_by(event_action="auth.login.failed").one()
        assert row.outcome == "failure"
        assert row.severity == "medium"
        assert "rahasia@example.test" not in row.actor_email
        assert "PasswordYangSalah123" not in row.detail


def test_notifikasi_signature_invalid_dicatat_sebagai_event_payment(client, app, midtrans_ready):
    daftar_dan_login(client, email="payaudit@test.local", nama="Payment Audit")
    address_id = buat_alamat(client)
    created = client.post("/customer/api/orders", json={
        "address_id": address_id, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1,
    })
    assert created.status_code == 201
    order = client.get("/customer/api/orders").get_json()[0]
    data = {
        "order_id": order["orderNumber"], "status_code": "200",
        "gross_amount": f"{order['total']}.00", "transaction_status": "settlement",
        "fraud_status": "accept", "signature_key": "0" * 128,
    }
    public_client = app.test_client()
    response = public_client.post("/midtrans/notifikasi", json=data)
    assert response.status_code == 403
    with app.app_context():
        row = AuditLog.query.filter_by(event_action="payment.signature_invalid").one()
        assert row.event_category == "payment"
        assert row.outcome == "rejected"
        assert row.severity == "high"
        assert "signature_key" not in json.dumps(row.context_data or {}).lower()


def test_halaman_audit_mendukung_filter_pencarian_dan_paginasi(client, app):
    login_admin(client)
    with app.app_context():
        from app.utils import audit
        audit.catat("produk_dibuat", "product", 901, "Produk Audit Filter", commit=True)
        audit.catat("midtrans_signature_invalid", "order", "ORD-UNKNOWN", "Signature invalid", actor_role="gateway", commit=True)

    semua = client.get("/admin/audit")
    assert semua.status_code == 200
    assert b"Audit Log" in semua.data
    filtered = client.get("/admin/audit?kategori=payment&severity=high&q=ORD-UNKNOWN")
    assert filtered.status_code == 200
    assert b"payment.signature_invalid" in filtered.data
    assert b"Produk Audit Filter" not in filtered.data


def test_audit_log_tidak_dapat_diakses_customer(client):
    daftar_dan_login(client)
    assert client.get("/admin/audit").status_code == 403


def test_audit_jsonl_tidak_mencatat_transaksi_rollback(app, tmp_path):
    target = tmp_path / "logs" / "rollback.jsonl"
    app.config["AUDIT_LOG_FILE"] = str(target)
    with app.app_context():
        from app.utils import audit
        audit.catat("produk_dibuat", "product", 999, "Tidak jadi dibuat")
        db.session.rollback()
    assert not target.exists()


def test_akses_order_customer_lain_dicatat_sebagai_payment_anomaly(app, midtrans_ready):
    pemilik, penyerobot = app.test_client(), app.test_client()
    daftar_dan_login(pemilik, email="owner-audit@test.local", nama="Pemilik Audit")
    address_id = buat_alamat(pemilik)
    created = pemilik.post("/customer/api/orders", json={
        "address_id": address_id, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1,
    })
    assert created.status_code == 201
    with app.app_context():
        from app.models import Order, User
        owner = User.query.filter_by(email="owner-audit@test.local").one()
        order_id = Order.query.filter_by(user_id=owner.id).one().id
    daftar_dan_login(penyerobot, email="other-audit@test.local", nama="Pengguna Lain")
    response = penyerobot.post(f"/customer/api/orders/{order_id}/midtrans")
    assert response.status_code == 404
    with app.app_context():
        row = AuditLog.query.filter_by(event_action="payment.unauthorized_access").one()
        assert row.event_category == "payment"
        assert row.severity == "high"
        assert row.outcome == "blocked"
        assert row.context_data["attempted_action"] == "read_payment_status"


def test_akses_bukti_pembayaran_customer_lain_ditandai_high(client, app, midtrans_ready):
    daftar_dan_login(client, email="proof-owner@test.local", nama="Pemilik Bukti")
    address_id = buat_alamat(client)
    created = client.post("/customer/api/orders", json={
        "address_id": address_id, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1,
    })
    assert created.status_code == 201
    with app.app_context():
        from app.models import Order, User
        owner = User.query.filter_by(email="proof-owner@test.local").one()
        order = Order.query.filter_by(user_id=owner.id).one()
        payment_id = order.payment.id
        order.payment.proof_path = "/tmp/nonexistent-payment-proof-test.pdf"
        db.session.commit()

    other = app.test_client()
    daftar_dan_login(other, email="proof-other@test.local", nama="Pengguna Lain")
    response = other.get(f"/media/payments/{payment_id}")
    assert response.status_code == 403
    with app.app_context():
        rows = AuditLog.query.filter_by(event_action="payment.unauthorized_access").all()
        row = next(item for item in rows if item.context_data.get("attempted_action") == "download_payment_proof")
        assert row.severity == "high"
        assert row.outcome == "blocked"
        assert len(rows) == 1  # tidak dibuat lagi sebagai generic HTTP 403

def test_perubahan_profil_customer_dicatat_di_audit_log(client, app):
    email = "profil-audit@test.local"
    daftar_dan_login(client, email=email, nama="Profil Audit")

    with app.app_context():
        user = User.query.filter_by(email=email).one()

        event_sebelum = {
            row.event_id
            for row in AuditLog.query.filter_by(
                event_action="customer.profile.updated",
                actor_id=user.id,
                target_id=str(user.id),
            ).all()
        }

    response = client.put("/customer/api/profile", json={
        "nama": "Profil Audit Baru",
        "email": email,
        "telepon": "081234567891",
    })

    assert response.status_code == 200

    with app.app_context():
        rows = AuditLog.query.filter_by(
            event_action="customer.profile.updated",
            actor_id=user.id,
            target_id=str(user.id),
        ).all()

        event_baru = [
            row for row in rows
            if row.event_id not in event_sebelum
        ]

        assert len(event_baru) == 1

        row = event_baru[0]
        assert row.event_category == "commerce"
        assert row.actor_role == "customer"
        assert row.target_type == "user"
        assert row.context_data["changed_fields"] == ["nama", "telepon"]


def test_perubahan_alamat_customer_dicatat_di_audit_log(client, app):
    daftar_dan_login(
        client,
        email="alamat-audit@test.local",
        nama="Alamat Audit",
    )

    response = client.put("/customer/api/addresses", json={
        "daftar": [{
            "id": "",
            "label": "Rumah",
            "penerima": "Alamat Audit",
            "telepon": "081234567890",
            "kodePos": "29461",
            "provinsi": "Kepulauan Riau",
            "kota": "Batam",
            "kecamatan": "Batam Kota",
            "lengkap": "Jl. Contoh No. 1 Batam",
        }],
        "utamaId": "",
    })

    assert response.status_code == 200

    with app.app_context():
        row = AuditLog.query.filter_by(
            event_action="customer.addresses.updated"
        ).one()

        assert row.event_category == "commerce"
        assert row.actor_role == "customer"
        assert row.target_type == "user"
        assert row.context_data["address_count"] == 1
        assert row.context_data["has_primary_address"] is True