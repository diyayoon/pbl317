"""Pencarian produk: parsial, multi-kata, huruf besar-kecil, kosong, karakter khusus, dan sinkron dengan database."""
import re

import pytest

from app.extensions import db
from app.models import Category, Product
from app.services.catalog_service import CatalogService
from tests.conftest import login_admin


def _tambah(nama, kategori, material="Kayu Jati", deskripsi="", asal="Jawa", era="1900–1949", aktif=True):
    kat = Category.query.filter_by(name=kategori).first() or Category(name=kategori, slug=re.sub(r"\W+", "-", kategori.lower()), icon="◆")
    db.session.add(Product(category=kat, name=nama, slug=re.sub(r"\W+", "-", nama.lower()), description=deskripsi, price=500000,
                           stock=2, era=era, origin=asal, material=material, condition="Good", authenticity_status="Verified",
                           image_alt=nama, is_active=aktif))
    db.session.commit()


@pytest.fixture()
def toko(app):
    with app.app_context():
        _tambah("Kursi Kayu Vintage", "Furnitur", material="Kayu Mahoni", deskripsi="Kursi makan klasik.")
        _tambah("Meja Marmer Vintage", "Furnitur", material="Marmer", deskripsi="Meja teras bergaya art deco.")
        _tambah("Lemari Hias", "Furnitur", material="Kayu Jati", deskripsi="Lemari pajangan dengan kaca.")
        _tambah("Teko Porselen", "Keramik", material="Porselen", deskripsi="Teko teh dari Tiongkok.", asal="Tiongkok")
        _tambah("Piring Tersembunyi", "Keramik", material="Porselen", aktif=False)
    return app


def _nama(app, q, **kw):
    with app.app_context():
        return [p["nama"] for p in CatalogService.list_products(query=q, **kw)]


def test_kata_parsial_dan_bidang_relevan(toko):
    assert _nama(toko, "kursi") == ["Kursi Kayu Vintage"]
    assert _nama(toko, "urs") == ["Kursi Kayu Vintage"]
    assert set(_nama(toko, "kayu")) == {"Kursi Kayu Vintage", "Lemari Hias"}  # nama dan material
    assert _nama(toko, "tiongkok") == ["Teko Porselen"]                      # asal
    assert set(_nama(toko, "keramik")) == {"Teko Porselen"}                  # nama kategori
    assert _nama(toko, "art deco") == ["Meja Marmer Vintage"]                # deskripsi


def test_multi_kata_semua_cocok_didahulukan(toko):
    hasil = _nama(toko, "meja vintage")
    assert hasil[0] == "Meja Marmer Vintage"             # cocok dua kata
    assert "Kursi Kayu Vintage" in hasil                 # cocok satu kata, tetap ditemukan
    assert "Teko Porselen" not in hasil
    assert _nama(toko, "kursi vintage")[0] == "Kursi Kayu Vintage"


def test_nama_lebih_relevan_daripada_deskripsi(toko):
    with toko.app_context():
        _tambah("Hiasan Dinding", "Dekor", material="Besi", deskripsi="Cocok untuk ruang dengan kursi antik.")
    assert _nama(toko, "kursi")[0] == "Kursi Kayu Vintage"


def test_huruf_besar_kecil_dan_spasi_konsisten(toko):
    ref = _nama(toko, "kursi kayu")
    assert _nama(toko, "KURSI KAYU") == ref == _nama(toko, "  kursi    kayu  ") == _nama(toko, "KuRsI\tkAyU")


def test_input_kosong_menampilkan_semua_produk_aktif(toko):
    semua = _nama(toko, "")
    assert len(semua) == 5 and "Jam Saku Uji" in semua and "Piring Tersembunyi" not in semua  # 4 produk toko + 1 dari fixture dasar
    assert _nama(toko, "   ") == semua


def test_produk_nonaktif_tidak_pernah_muncul(toko):
    assert _nama(toko, "piring") == [] and _nama(toko, "tersembunyi") == []


@pytest.mark.parametrize("q", ["%", "_", "\\", "'", "\"; DROP TABLE products; --", "' OR '1'='1", "a%b", "x" * 500, "<script>"])
def test_karakter_khusus_aman_dan_wildcard_dianggap_biasa(toko, q):
    hasil = _nama(toko, q)
    assert len(hasil) < 5      # '%' dan '_' tidak berarti "cocok semua" (5 produk aktif)
    with toko.app_context():
        assert Product.query.count() == 6          # tabel tidak tersentuh


def test_halaman_kosong_menampilkan_pesan_dan_cara_ulang(client, toko):
    html = client.get("/katalog?q=tidakadaproduk").get_data(as_text=True)
    assert 'id="productCount">0<' in html and "Tidak ada koleksi yang sesuai" in html and 'id="catalogEmptyReset"' in html


def test_katalog_menerapkan_q_dan_mengisi_kotak_pencarian(client, toko):
    html = client.get("/katalog?q=kursi").get_data(as_text=True)
    assert "Kursi Kayu Vintage" in html and "Teko Porselen" not in html and 'value="kursi"' in html


def test_fragment_hasil_memakai_kartu_yang_sama_dengan_atribut_filter(client, toko):
    html = client.get("/katalog/hasil?q=meja vintage").get_data(as_text=True)
    assert html.index("Meja Marmer Vintage") < html.index("Kursi Kayu Vintage")  # urutan relevansi
    for atribut in ("data-category=", "data-price=", "data-era=", "data-condition=", "data-id="):
        assert atribut in html                                   # filter/sort/paginasi klien tetap bekerja
    assert client.get("/katalog/hasil?q=kursi").headers["Cache-Control"] == "no-store"


def test_input_diberi_escape_di_html(client, toko):
    html = client.get('/katalog?q="><script>alert(1)</script>').get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html


def test_filter_kategori_bersama_pencarian(toko):
    with toko.app_context():
        slug = Category.query.filter_by(name="Furnitur").one().slug
    assert set(_nama(toko, "vintage", category_slug=slug)) == {"Kursi Kayu Vintage", "Meja Marmer Vintage"}
    assert _nama(toko, "vintage", category_slug="keramik") == []


def test_perubahan_admin_langsung_tercermin_di_hasil(app, toko):
    adm, pub = app.test_client(), app.test_client()
    login_admin(adm)
    payload = {"nama": "Gramofon Antik Himalaya", "kategori": "Furnitur", "era": "1900–1949", "asal": "Eropa", "kondisi": "Good",
               "material": "Logam", "autentikasi": "Verified", "deskripsi": "Gramofon kerja.", "harga": 2500000, "stok": 1, "gambar": ""}
    r = adm.post("/admin/api/produk", json=payload)
    assert r.status_code in (200, 201), r.get_json()
    pid = r.get_json()["product"]["id"]
    assert "Gramofon Antik Himalaya" in pub.get("/katalog/hasil?q=himalaya").get_data(as_text=True)      # produk baru
    payload["nama"] = "Fonograf Antik Alpen"
    assert adm.put(f"/admin/api/produk/{pid}", json=payload).status_code == 200
    assert "Gramofon" not in pub.get("/katalog/hasil?q=himalaya").get_data(as_text=True)                  # nama lama hilang
    assert "Fonograf Antik Alpen" in pub.get("/katalog/hasil?q=alpen").get_data(as_text=True)             # nama baru muncul
    assert adm.post(f"/admin/api/produk/{pid}/status", json={"aktif": False}).status_code == 200
    assert "Fonograf" not in pub.get("/katalog/hasil?q=alpen").get_data(as_text=True)                     # dinonaktifkan
    assert adm.delete(f"/admin/api/produk/{pid}").status_code == 200
    assert "Fonograf" not in pub.get("/katalog?q=alpen").get_data(as_text=True)                           # dihapus


def test_upload_produk_multipart(app, toko):
    import io
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    adm = app.test_client()
    login_admin(adm)
    data = {"nama": "Lampu Minyak Antik", "kategori": "Furnitur", "era": "1900–1949", "asal": "Eropa", "kondisi": "Good",
            "material": "Kuningan", "autentikasi": "Verified", "deskripsi": "Lampu kerja.", "harga": "1500000", "stok": "2",
            "gambar": (io.BytesIO(png), "lampu.png")}
    r = adm.post("/admin/api/produk", data=data, content_type="multipart/form-data")
    assert r.status_code == 201, r.get_json()
    produk = r.get_json()["product"]
    assert produk["gambar"].startswith("/media/products/")
    assert adm.get(produk["gambar"]).status_code == 200
    # isi bukan gambar ditolak
    data["gambar"] = (io.BytesIO(b"bukan gambar"), "palsu.png")
    r = adm.post("/admin/api/produk", data=data, content_type="multipart/form-data")
    assert r.status_code == 422 and "gambar" in r.get_json()["errors"]
    # edit tanpa file baru: foto lama tetap
    data.pop("gambar")
    r = adm.put(f"/admin/api/produk/{produk['id']}", data=data, content_type="multipart/form-data")
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["product"]["gambar"] == produk["gambar"]
