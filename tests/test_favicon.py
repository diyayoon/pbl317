"""Favicon terpasang di semua halaman dan berkasnya benar-benar tersaji."""
import re

from PIL import Image
import io


def test_semua_halaman_memuat_tautan_favicon(client):
    for url in ("/", "/katalog", "/auth/login", "/auth/register"):
        html = client.get(url).get_data(as_text=True)
        assert 'rel="icon"' in html and "images/favicon/favicon.ico" in html and 'rel="apple-touch-icon"' in html, url


def test_berkas_favicon_tersaji_dan_berukuran_benar(client):
    html = client.get("/").get_data(as_text=True)
    href = re.findall(r'<link rel="(?:icon|apple-touch-icon)"[^>]*href="([^"]+)"', html)
    assert len(href) == 5
    for h in href:
        r = client.get(h)
        assert r.status_code == 200 and r.mimetype.startswith("image/"), h
        assert len(r.data) < 60_000, h                       # ringan, bukan gambar 1,4 MB asli
    assert Image.open(io.BytesIO(client.get(next(h for h in href if h.endswith("favicon-32.png"))).data)).size == (32, 32)
    assert Image.open(io.BytesIO(client.get(next(h for h in href if h.endswith("favicon-192.png"))).data)).size == (192, 192)
    ico = Image.open(io.BytesIO(client.get(next(h for h in href if h.endswith(".ico"))).data))
    assert {(16, 16), (32, 32), (48, 48)} <= set(ico.info.get("sizes", {(48, 48)}))


def test_favicon_ico_di_akar_dialihkan_bukan_404(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 301 and r.headers["Location"].endswith("/static/images/favicon/favicon.ico")
