from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Category, Order, Product, Review
from app.services import midtrans_service as ms
from tests.conftest import buat_alamat, daftar_dan_login, login_admin

PNG = b"\x89PNG\r\n\x1a\n" + b"1" * 100


def _pesan(client, alamat, qty=1, metode="Midtrans"):
    return client.post("/customer/api/orders", json={"address_id": alamat, "payment_method": metode, "direct_product_id": 1, "quantity": qty})


def test_katalog_menampilkan_produk_database(client):
    r = client.get("/katalog")
    assert r.status_code == 200 and b"Jam Saku Uji" in r.data
    # filter kategori di URL tidak boleh menyaring di server (JS yang menyaring)
    assert client.get("/katalog?kategori=tidak-ada").data.count(b"data-product") == r.data.count(b"data-product")
    detail = client.get("/produk/1").get_data(as_text=True)
    assert 'id="detailOpenCart"' in detail and 'id="detailBuyNow"' in detail
    assert "Ulasan pembeli" in detail and "Koleksi terkait" not in detail


def test_foto_kategori_tidak_mengikuti_foto_produk(client, app):
    from app.services.catalog_service import CatalogService
    with app.app_context():
        kategori = db.session.get(Category, 1)
        kategori.image_url = "/static/images/categories/jam-timepiece.jpg"
        db.session.commit()
        awal = CatalogService.category_summary()[0]["gambar"]
        produk = db.session.get(Product, 1)
        produk.images[0].image_url = "https://example.com/foto-produk-baru.jpg"
        db.session.commit()
        akhir = CatalogService.category_summary()[0]["gambar"]
    assert awal == akhir == "/static/images/categories/jam-timepiece.jpg"


def test_checkout_harga_dihitung_server_dan_stok_berkurang(client, app, midtrans_ready):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    r = _pesan(client, alamat, qty=2)
    assert r.status_code == 201 and r.get_json()["order"]["total"] == 2_000_000 + 25_000   # subtotal + ongkir tetap
    with app.app_context():
        assert db.session.get(Product, 1).stock == 1
    assert _pesan(client, alamat, qty=5).status_code == 422          # stok kurang


def test_alamat_milik_orang_lain_ditolak(app, midtrans_ready):
    a, b = app.test_client(), app.test_client()
    daftar_dan_login(a)
    alamat_a = buat_alamat(a)
    daftar_dan_login(b, email="lain@test.local")
    assert _pesan(b, alamat_a).status_code == 404


def test_batas_pesanan_terbuka(client, app, midtrans_ready):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    with app.app_context():
        db.session.get(Product, 1).stock = 50
        db.session.commit()
    kode = [_pesan(client, alamat).status_code for _ in range(6)]
    assert kode == [201] * 5 + [422]


def test_pesanan_kedaluwarsa_dibatalkan_dan_stok_kembali(client, app, midtrans_ready):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    oid = _pesan(client, alamat, qty=2).get_json()["order"]["id"]
    with app.app_context():
        db.session.get(Order, oid).created_at = datetime.now(timezone.utc) - timedelta(hours=30)
        db.session.commit()
    pesanan = client.get("/customer/api/orders").get_json()[0]
    assert pesanan["status"] == "Dibatalkan" and pesanan["statusPembayaran"] == "Kedaluwarsa"
    with app.app_context():
        assert db.session.get(Product, 1).stock == 3


def test_alur_midtrans_status_ulasan_foto_dan_moderasi(app, midtrans_ready):
    cust, adm = app.test_client(), app.test_client()
    daftar_dan_login(cust)
    alamat = buat_alamat(cust)
    dibuat = _pesan(cust, alamat)
    assert dibuat.status_code == 201
    oid = dibuat.get_json()["order"]["id"]

    # Pesanan Midtrans tidak lagi menerima unggahan bukti manual.
    import io
    r = cust.post(f"/customer/api/orders/{oid}/bukti", data={"buktiBayar": (io.BytesIO(PNG), "bukti.png")}, content_type="multipart/form-data")
    assert r.status_code in (400, 409, 422)
    assert cust.post("/customer/api/reviews", json={"product_id": 1, "rating": 4}).status_code == 403  # belum selesai

    # Simulasikan notifikasi settlement yang sudah diverifikasi oleh Midtrans.
    with app.test_request_context("/midtrans/notifikasi", method="POST"):
        order = db.session.get(Order, oid)
        hasil = ms.LayananMidtrans.terapkan({
            "order_id": order.order_number, "gross_amount": f"{int(order.total)}.00",
            "transaction_status": "settlement", "fraud_status": "accept",
            "payment_type": "qris", "transaction_id": "uji-settlement",
        })
        assert hasil == "lunas" and order.status == "Diproses" and order.payment.status == "Disetujui"

    login_admin(adm)
    for status in ("Dikirim", "Selesai"):
        assert adm.patch(f"/admin/api/pesanan/{oid}", json={"status": status}).status_code == 200
    assert adm.patch(f"/admin/api/pesanan/{oid}", json={"status": "Diproses"}).status_code == 422

    # Ulasan satu kali, maksimal tujuh hari, dan foto opsional.
    data = {"product_id": "1", "rating": "4", "komentar": "<b>Bagus</b>", "gambarUlasan": (io.BytesIO(PNG), "ulasan.png")}
    ulas = cust.post("/customer/api/reviews", data=data, content_type="multipart/form-data")
    assert ulas.status_code == 201
    review = ulas.get_json()["review"]
    assert review["gambar_url"] == f"/media/reviews/{review['id']}"
    assert cust.get(review["gambar_url"]).status_code == 200
    assert cust.post("/customer/api/reviews", json={"product_id": 1, "rating": 5}).status_code == 422

    lain = app.test_client()
    daftar_dan_login(lain, email="lain@test.local")
    assert lain.post("/customer/api/reviews", json={"product_id": 1, "rating": 5}).status_code == 403
    halaman = cust.get("/produk/1").data
    assert b"&lt;b&gt;Bagus" in halaman and b"<b>Bagus</b>" not in halaman

    rid = adm.get("/admin/api/ulasan").get_json()[0]["id"]
    assert adm.post(f"/admin/api/ulasan/{rid}/moderasi", json={"sembunyikan": True}).status_code == 422
    assert adm.post(f"/admin/api/ulasan/{rid}/moderasi", json={"sembunyikan": True, "alasan": "Melanggar"}).status_code == 200
    assert b"Bagus" not in cust.get("/produk/1").data
    assert cust.get(review["gambar_url"]).status_code == 404  # foto ulasan tersembunyi tidak dapat diakses publik
    with app.app_context():
        assert db.session.get(Product, 1).ulasan == 0 and Review.query.count() == 1


def test_dashboard_total_pesanan_bukan_dibatasi_tiga(client, app, midtrans_ready):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    with app.app_context():
        db.session.get(Product, 1).stock = 20
        db.session.commit()
    for _ in range(4):
        _pesan(client, alamat)
    ringkasan = client.get("/customer/api/dashboard-summary").get_json()
    assert ringkasan["order_count"] == 4 and len(ringkasan["orders"]) == 3


def test_kategori_dan_produk_dihapus_aman(client, app, midtrans_ready):
    daftar_dan_login(client)
    alamat = buat_alamat(client)
    _pesan(client, alamat)
    adm = app.test_client()
    login_admin(adm)
    # produk yang pernah dipesan -> dinonaktifkan, riwayat tetap utuh
    r = adm.delete("/admin/api/produk/1")
    assert r.get_json()["hasil"] == "dinonaktifkan"
    assert client.get("/customer/api/orders").get_json()[0]["items"][0]["nama"] == "Jam Saku Uji"
    assert b"Jam Saku Uji" not in client.get("/katalog").data
    # kategori yang masih dipakai produk -> dinonaktifkan
    kid = adm.get("/admin/api/kategori").get_json()[0]["id"]
    assert adm.delete(f"/admin/api/kategori/{kid}").get_json()["hasil"] == "dinonaktifkan"
    baru_resp = adm.post("/admin/api/kategori", data={"nama": "Kategori Kosong", "gambar": (__import__("io").BytesIO(PNG), "kategori.png")}, content_type="multipart/form-data")
    assert baru_resp.status_code == 201
    kategori_baru = baru_resp.get_json()["kategori"][-1]
    assert kategori_baru["gambar"].startswith("/media/categories/")
    assert adm.get(kategori_baru["gambar"]).status_code == 200
    baru = kategori_baru["id"]
    assert adm.delete(f"/admin/api/kategori/{baru}").get_json()["hasil"] == "dihapus"
    with app.app_context():
        assert db.session.get(Category, kid).is_active is False


def test_email_profil_tidak_bisa_diubah(client):
    daftar_dan_login(client)
    r = client.put("/customer/api/profile", json={"nama": "Pembeli Uji", "email": "baru@test.local", "telepon": "081234567890"})
    assert r.status_code == 422
