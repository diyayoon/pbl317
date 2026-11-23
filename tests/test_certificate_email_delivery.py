"""Pengujian email sertifikat setelah Midtrans diverifikasi server-to-server."""
import hashlib
from io import BytesIO
from pathlib import Path

from werkzeug.datastructures import MultiDict

from app.extensions import db
from app.models import CertificateEmailDelivery, Order, Product
from app.services import midtrans_service as ms
from tests.conftest import buat_alamat, daftar_dan_login, login_admin

SERVER_KEY = "SB-Mid-server-CERTIFICATE-EMAIL-TEST"


def _product_payload():
    return {
        "nama": "Jam Saku Bersertifikat",
        "kategori": "Jam & Timepiece",
        "era": "1900–1949",
        "asal": "Swiss",
        "kondisi": "Good",
        "material": "Kuningan",
        "autentikasi": "Documented",
        "deskripsi": "Jam saku antik dengan dokumen sertifikat.",
        "harga": "1000000",
        "stok": "3",
    }


def _signature(order_number, amount):
    source = f"{order_number}200{amount}{SERVER_KEY}"
    return hashlib.sha512(source.encode()).hexdigest()


def test_sertifikat_pdf_dikirim_setelah_midtrans_settlement_dan_tidak_duplikat(
    client, app, tmp_path, midtrans_ready, monkeypatch
):
    from app.services import certificate_delivery_service as delivery_service

    # Sertifikat produk dibuat oleh admin dan disimpan privat.
    certificate_folder = tmp_path / "certificates"
    app.config["PRODUCT_CERTIFICATE_UPLOAD_FOLDER"] = str(certificate_folder)
    admin = app.test_client()
    login_admin(admin)
    product_data = MultiDict(_product_payload().items())
    pdf_original = b"%PDF-1.4\nSertifikat Albis Antique asli\n%%EOF"
    product_data.add("sertifikat", (BytesIO(pdf_original), "coa-jam-saku.pdf", "application/pdf"))
    upload = admin.put("/admin/api/produk/1", data=product_data, content_type="multipart/form-data")
    assert upload.status_code == 200, upload.get_json()

    # Checkout membuat transaksi Midtrans sandbox palsu tanpa jaringan.
    app.config.update(
        MIDTRANS_SERVER_KEY=SERVER_KEY,
        MIDTRANS_IS_PRODUCTION=False,
        APP_BASE_URL="http://localhost:5000",
    )
    customer = app.test_client()
    daftar_dan_login(customer, email="certificate-buyer@test.local", nama="Pembeli Sertifikat")
    address_id = buat_alamat(customer)
    checkout = customer.post("/customer/api/orders", json={
        "address_id": address_id, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1,
    })
    assert checkout.status_code == 201, checkout.get_json()
    order_payload = checkout.get_json()["order"]
    order_number = order_payload["orderNumber"]
    gross_amount = f"{order_payload['total']}.00"

    # Status GET yang diterima backend harus berasal dari jawaban resmi Midtrans (di-mock di test ini).
    def fake_status(method, url, body=None):
        if method == "GET":
            return 200, {
                "order_id": order_number,
                "status_code": "200",
                "gross_amount": gross_amount,
                "transaction_status": "settlement",
                "fraud_status": "accept",
                "payment_type": "qris",
                "transaction_id": "certificate-email-test-transaction",
            }
        return 201, {"redirect_url": "https://app.sandbox.midtrans.com/snap/v4/redirection/test"}

    monkeypatch.setattr(ms, "_http", fake_status)
    monkeypatch.setattr(delivery_service, "smtp_terkonfigurasi", lambda: True)
    sent = []

    def fake_send(to, subject, body, attachments):
        sent.append({"to": to, "subject": subject, "attachments": attachments})
        return True

    monkeypatch.setattr(delivery_service, "kirim_email_dengan_lampiran", fake_send)

    notification = {
        "order_id": order_number,
        "status_code": "200",
        "gross_amount": gross_amount,
        "transaction_status": "settlement",
        "fraud_status": "accept",
        "payment_type": "qris",
        "transaction_id": "certificate-email-test-transaction",
    }
    notification["signature_key"] = _signature(order_number, gross_amount)
    webhook = app.test_client()
    first = webhook.post("/midtrans/notifikasi", json=notification)
    assert first.status_code == 200, first.get_json()
    assert len(sent) == 1
    assert sent[0]["to"] == "certificate-buyer@test.local"
    assert len(sent[0]["attachments"]) == 1
    assert sent[0]["attachments"][0]["filename"].endswith(".pdf")
    assert sent[0]["attachments"][0]["data"] == pdf_original

    # Callback yang sama tidak mengirim email kedua kali.
    duplicate = webhook.post("/midtrans/notifikasi", json=notification)
    assert duplicate.status_code == 200
    assert len(sent) == 1
    with app.app_context():
        order = Order.query.filter_by(order_number=order_number).one()
        record = CertificateEmailDelivery.query.filter_by(order_id=order.id).one()
        assert order.payment.status == "Disetujui"
        assert order.status == "Diproses"
        assert record.status == "sent"
        assert record.attempt_count == 1
        assert record.attachment_count == 1
