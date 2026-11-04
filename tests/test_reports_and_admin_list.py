from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime
from io import BytesIO
from openpyxl import load_workbook

from app.extensions import db
from app.models import Order
from tests.conftest import buat_alamat, daftar_dan_login, login_admin


def test_admin_page_pengguna_memuat_javascript_dan_daftar_admin_readonly(client):
    admin = client.application.test_client()
    login_admin(admin)
    html = admin.get("/admin/pengguna").get_data(as_text=True)
    assert 'id="userRows"' in html and 'id="adminAccountRows"' in html
    assert 'js/admin.js' in html
    admins = admin.get("/admin/api/admin").get_json()
    assert any(row["email"] == "admin@albis.local" for row in admins)
    assert admin.post("/admin/api/admin").status_code == 405


def test_admin_list_customers_and_admins_separate(client, app):
    daftar_dan_login(client)
    admin = app.test_client(); login_admin(admin)
    customers = admin.get("/admin/api/pengguna").get_json()
    admins = admin.get("/admin/api/admin").get_json()
    assert any(row["email"] == "pembeli@test.local" for row in customers)
    assert all(row["email"] != "admin@albis.local" for row in customers)
    assert all(row["email"] != "pembeli@test.local" for row in admins)


def test_report_page_date_filter_and_export_pdf_excel(app, client, midtrans_ready):
    daftar_dan_login(client)
    address_id = buat_alamat(client)
    response = client.post("/customer/api/orders", json={
        "address_id": address_id, "payment_method": "Midtrans", "direct_product_id": 1, "quantity": 1,
    })
    assert response.status_code == 201
    order = response.get_json()["order"]
    with app.app_context():
        row = db.session.get(Order, order["id"])
        row.status = "Selesai"
        row.payment.status = "Disetujui"
        db.session.commit()
    admin = app.test_client(); login_admin(admin)
    today = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    api = admin.get(f"/admin/api/laporan?tanggal_awal={today}&tanggal_akhir={today}")
    assert api.status_code == 200
    assert api.get_json()["selesai"] == 1
    assert api.get_json()["pendapatan"] == order["total"]
    assert admin.get(f"/admin/laporan?tanggal_awal={today}&tanggal_akhir={today}").status_code == 200
    pdf = admin.get(f"/admin/laporan/export.pdf?tanggal_awal={today}&tanggal_akhir={today}")
    xlsx = admin.get(f"/admin/laporan/export.xlsx?tanggal_awal={today}&tanggal_akhir={today}")
    assert pdf.status_code == 200 and pdf.mimetype == "application/pdf" and pdf.data.startswith(b"%PDF")
    assert xlsx.status_code == 200 and "spreadsheetml" in xlsx.mimetype and xlsx.data[:2] == b"PK"
    workbook = load_workbook(BytesIO(xlsx.data))
    sheet = workbook["Penjualan"]
    assert sheet.freeze_panes is None
    assert len(sheet.tables) == 1
    assert sheet.column_dimensions["D"].width >= 30
    assert sheet["A1"].value == "LAPORAN PENJUALAN ALBIS ANTIQUE"
