"""Regression test galeri foto produk (maksimal lima foto, satu foto utama)."""
from io import BytesIO
from pathlib import Path

from werkzeug.datastructures import MultiDict

from tests.conftest import login_admin


def _payload():
    return {
        "nama": "Kamera Antik Galeri",
        "kategori": "Jam & Timepiece",
        "era": "1900–1949",
        "asal": "Swiss",
        "kondisi": "Good",
        "material": "Logam",
        "autentikasi": "Not verified",
        "deskripsi": "Kamera koleksi untuk pengujian galeri.",
        "harga": "1750000",
        "stok": "2",
    }


def _jpeg(label: bytes):
    # Endpoint memeriksa MIME dan signature; file kecil ini cukup untuk menguji alur penyimpanan.
    return BytesIO(b"\xff\xd8\xff" + label + b"-test-image")


def test_admin_dapat_mengunggah_beberapa_foto_dan_memilih_foto_utama(client, app, tmp_path):
    app.config["PRODUCT_UPLOAD_FOLDER"] = str(tmp_path / "products")
    login_admin(client)
    data = MultiDict(_payload().items())
    data.add("gambar", (_jpeg(b"front"), "front.jpg", "image/jpeg"))
    data.add("gambar", (_jpeg(b"side"), "side.jpg", "image/jpeg"))
    data.add("foto_utama_index", "1")

    response = client.post("/admin/api/produk", data=data, content_type="multipart/form-data")
    assert response.status_code == 201, response.get_json()
    product = response.get_json()["product"]
    assert len(product["gambar_list"]) == 2
    assert product["gambar"] == product["gambar_list"][1]["url"]
    assert [image["utama"] for image in product["gambar_list"]] == [False, True]
    assert all(Path(tmp_path / "products" / image["url"].rsplit("/", 1)[-1]).is_file() for image in product["gambar_list"])


def test_gallery_dapat_diperbarui_dengan_menghapus_dan_menambah_foto(client, app, tmp_path):
    app.config["PRODUCT_UPLOAD_FOLDER"] = str(tmp_path / "products")
    login_admin(client)
    data = MultiDict(_payload().items())
    data.add("gambar", (_jpeg(b"front"), "front.jpg", "image/jpeg"))
    data.add("gambar", (_jpeg(b"side"), "side.jpg", "image/jpeg"))
    created = client.post("/admin/api/produk", data=data, content_type="multipart/form-data")
    assert created.status_code == 201, created.get_json()
    product = created.get_json()["product"]
    foto_lama = product["gambar_list"][0]
    foto_dipertahankan = product["gambar_list"][1]
    old_path = tmp_path / "products" / foto_lama["url"].rsplit("/", 1)[-1]

    update = MultiDict(_payload().items())
    update.add("hapus_gambar_ids", str(foto_lama["id"]))
    update.add("gambar", (_jpeg(b"detail"), "detail.jpg", "image/jpeg"))
    update.add("foto_utama_index", "0")
    response = client.put(f"/admin/api/produk/{product['id']}", data=update, content_type="multipart/form-data")
    assert response.status_code == 200, response.get_json()
    changed = response.get_json()["product"]
    assert len(changed["gambar_list"]) == 2
    # foto_utama_index=0 menunjuk foto baru pertama; foto lama yang dipertahankan
    # tetap berada di posisi pertama, sedangkan foto baru menjadi foto utama.
    assert changed["gambar_list"][0]["utama"] is False
    assert changed["gambar_list"][1]["utama"] is True
    assert changed["gambar_list"][1]["id"] != foto_dipertahankan["id"]
    assert foto_dipertahankan["id"] in [image["id"] for image in changed["gambar_list"]]
    assert not old_path.exists()


def test_backend_menolak_total_foto_lebih_dari_lima(client, app, tmp_path):
    app.config["PRODUCT_UPLOAD_FOLDER"] = str(tmp_path / "products")
    login_admin(client)
    data = MultiDict(_payload().items())
    for index in range(6):
        data.add("gambar", (_jpeg(f"image-{index}".encode()), f"foto-{index}.jpg", "image/jpeg"))
    response = client.post("/admin/api/produk", data=data, content_type="multipart/form-data")
    assert response.status_code == 422
    assert "maksimal 5" in response.get_json()["error"].lower()
    assert not (tmp_path / "products").exists() or not list((tmp_path / "products").glob("*"))
