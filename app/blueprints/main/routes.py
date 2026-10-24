"""Route publik Albis Antique: beranda, katalog, detail produk (data dari PostgreSQL)."""
from flask import abort, make_response, render_template, request

from app.services.catalog_service import CatalogService
from app.services.review_service import LayananUlasan
from . import main_bp


def _pilih(products, ids):
    by_id = {item["id"]: item for item in products}
    return [by_id[i] for i in ids if i in by_id]


def _unik(*daftar, batas=6):
    terlihat, hasil = set(), []
    for item in (x for d in daftar for x in d):
        if item["id"] not in terlihat:
            terlihat.add(item["id"])
            hasil.append(item)
    return hasil[:batas]


@main_bp.get("/")
def beranda():
    """Etalase: unggulan = paling laku (jatuh ke produk terbaru bila belum ada penjualan)."""
    products = CatalogService.list_products()
    terbaru = products[:4]
    unggulan = _unik(_pilih(products, CatalogService.id_terlaris(4)), terbaru, batas=4)
    slide = _unik(unggulan, products, batas=6)
    return render_template(
        "main/index.html", kategori_unggulan=CatalogService.category_summary(),
        produk_unggulan=unggulan, produk_slide=slide, produk_terbaru=terbaru,
    )


@main_bp.get("/katalog")
def katalog():
    """Produk dari PostgreSQL. `?q=` dicari di server (berperingkat); filter lain, sortir, dan paginasi di catalog.js.

    `?kategori=<slug>` hanya menentukan pilihan awal dropdown, bukan menyaring di server.
    """
    q = " ".join(request.args.get("q", "").split())[:CatalogService.MAKS_PANJANG_Q]
    return render_template(
        "main/explore.html", kategori_unggulan=CatalogService.category_summary(),
        produk=CatalogService.list_products(query=q), kategori_awal=request.args.get("kategori", "")[:100], q_awal=q,
    )


@main_bp.get("/katalog/hasil")
def katalog_hasil():
    """Potongan HTML kartu produk (template yang sama dengan katalog) untuk pencarian langsung; selalu dari database."""
    q = " ".join(request.args.get("q", "").split())[:CatalogService.MAKS_PANJANG_Q]
    resp = make_response(render_template("main/_hasil_katalog.html", produk=CatalogService.list_products(query=q)))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@main_bp.get("/produk/<int:produk_id>")
def detail_produk(produk_id):
    product_model = CatalogService.get_product(produk_id)
    if product_model is None:
        abort(404)
    product = product_model.to_dict()
    products = CatalogService.list_products()
    terkait = [p for p in products if p["id"] != produk_id and p["slug_kategori"] == product["slug_kategori"]]
    lain = [p for p in products if p["id"] != produk_id and p not in terkait]
    return render_template(
        "main/product.html", produk=product, produk_id=produk_id,
        produk_terkait=(terkait + lain)[:4], daftar_ulasan=LayananUlasan.terlihat(produk_id),
    )
