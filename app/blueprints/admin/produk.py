"""Admin: produk dan kategori. (pemilik: Fiony)"""
from __future__ import annotations
from pathlib import Path
from flask import current_app, jsonify, render_template, request
from app.extensions import db
from app.models import Category
from app.services.catalog_service import CatalogService
from app.services.category_service import LayananKategori
from app.utils import audit
from app.utils.uploads import simpan_gambar_upload
from . import admin_bp
from app.utils.decorators import admin_required

PRODUCT_MAX_BYTES = 2 * 1024 * 1024


def _hapus_file_produk(url: str | None) -> None:
    """Hapus file foto produk lokal (hanya yang berada di folder upload produk)."""
    if not url or not url.startswith("/media/products/"):
        return
    base = Path(current_app.config["PRODUCT_UPLOAD_FOLDER"]).resolve()
    target = (base / url.rsplit("/", 1)[-1]).resolve()
    if base in target.parents and target.is_file():
        try:
            target.unlink()
        except OSError:
            current_app.logger.warning("Gagal menghapus file gambar produk %s", target.name)


def _hapus_upload_sementara(path: Path | None) -> None:
    if path and path.is_file():
        try:
            path.unlink()
        except OSError:
            current_app.logger.warning("Gagal membersihkan unggahan produk %s", path.name)


def _hapus_upload_sementara(path: Path | None) -> None:
    if path and path.is_file():
        try:
            path.unlink()
        except OSError:
            current_app.logger.warning("Gagal membersihkan unggahan produk %s", path.name)


def _baca_payload_produk():
    """Baca data produk; foto hanya diterima sebagai berkas multipart."""
    if request.mimetype != "multipart/form-data":
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            payload = dict(payload)
            if payload.get("gambar"):
                raise ValueError("Foto produk harus diunggah sebagai berkas, bukan melalui JSON.")
            payload.pop("gambar", None)
        return payload, None

    payload = request.form.to_dict()
    payload.pop("gambar", None)
    foto = request.files.get("gambar")
    if foto is None or not foto.filename:
        return payload, None

    batas = current_app.config.get("PRODUCT_MAX_BYTES", PRODUCT_MAX_BYTES)
    path = simpan_gambar_upload(foto, current_app.config["PRODUCT_UPLOAD_FOLDER"], batas)
    return payload, path


@admin_bp.get("/produk")
@admin_required
def produk():
    return render_template(
        "admin/products.html", produk_list=CatalogService.list_products(active_only=False),
        kategori_list=[c for c in LayananKategori.daftar() if c["aktif"]],
    )


@admin_bp.get("/kategori")
@admin_required
def kategori():
    return render_template("admin/categories.html")


@admin_bp.get("/api/produk")
@admin_required
def api_produk():
    return jsonify(CatalogService.list_products(active_only=False))


@admin_bp.post("/api/produk")
@admin_required
def api_tambah_produk():
    try:
        payload, path_baru = _baca_payload_produk()
    except ValueError as exc:
        return jsonify(error=str(exc), errors={"gambar": str(exc)}), 422

    image_url = f"/media/products/{path_baru.name}" if path_baru else ""
    try:
        product, errors = CatalogService.create_product(payload, image_url=image_url)
    except Exception:
        _hapus_upload_sementara(path_baru)
        raise
    if errors:
        _hapus_upload_sementara(path_baru)
        return jsonify(error="Periksa kembali data produk.", errors=errors), 422

    audit.catat("produk_dibuat", "product", product.id, product.name, commit=True)
    return jsonify(message="Produk berhasil disimpan.", product=product.to_dict(), products=CatalogService.list_products(active_only=False)), 201


@admin_bp.put("/api/produk/<int:produk_id>")
@admin_required
def api_ubah_produk(produk_id: int):
    existing = CatalogService.get_product(produk_id, active_only=False)
    if existing is None:
        return jsonify(error="Produk tidak ditemukan."), 404

    harga_lama = existing.harga
    gambar_lama = existing.gambar
    try:
        payload, path_baru = _baca_payload_produk()
    except ValueError as exc:
        return jsonify(error=str(exc), errors={"gambar": str(exc)}), 422

    image_url = f"/media/products/{path_baru.name}" if path_baru else ""
    try:
        product, errors = CatalogService.update_product(existing, payload, image_url=image_url)
    except Exception:
        _hapus_upload_sementara(path_baru)
        raise
    if errors:
        _hapus_upload_sementara(path_baru)
        return jsonify(error="Periksa kembali data produk.", errors=errors), 422

    if path_baru and gambar_lama != product.gambar:
        _hapus_file_produk(gambar_lama)
    audit.catat("produk_diubah", "product", product.id, f"{product.name}; harga {harga_lama}->{product.harga}", commit=True)
    return jsonify(message="Perubahan produk tersimpan.", product=product.to_dict(), products=CatalogService.list_products(active_only=False))


@admin_bp.post("/api/produk/<int:produk_id>/status")
@admin_required
def api_status_produk(produk_id: int):
    existing = CatalogService.get_product(produk_id, active_only=False)
    if existing is None:
        return jsonify(error="Produk tidak ditemukan."), 404
    aktif = bool((request.get_json(silent=True) or {}).get("aktif"))
    CatalogService.set_active(existing, aktif)
    audit.catat("produk_diaktifkan" if aktif else "produk_dinonaktifkan", "product", produk_id, existing.name, commit=True)
    return jsonify(message="Produk diaktifkan." if aktif else "Produk dinonaktifkan dari katalog.", products=CatalogService.list_products(active_only=False))


@admin_bp.delete("/api/produk/<int:produk_id>")
@admin_required
def api_hapus_produk(produk_id: int):
    existing = CatalogService.get_product(produk_id, active_only=False)
    if existing is None:
        return jsonify(error="Produk tidak ditemukan."), 404
    nama = existing.name
    hasil = CatalogService.delete_product(existing)
    audit.catat(f"produk_{hasil}", "product", produk_id, nama, commit=True)
    pesan = "Produk dihapus." if hasil == "dihapus" else "Produk sudah ada di riwayat pesanan, jadi dinonaktifkan (riwayat tetap utuh)."
    return jsonify(message=pesan, hasil=hasil, id=produk_id, products=CatalogService.list_products(active_only=False))


@admin_bp.get("/api/kategori")
@admin_required
def api_kategori():
    return jsonify(LayananKategori.daftar())


@admin_bp.post("/api/kategori")
@admin_required
def api_tambah_kategori():
    payload = request.form.to_dict() if request.mimetype == "multipart/form-data" else (request.get_json(silent=True) or {})
    foto = request.files.get("gambar")
    path = None
    try:
        path = simpan_gambar_upload(foto, current_app.config["CATEGORY_UPLOAD_FOLDER"], current_app.config["CATEGORY_MAX_BYTES"])
        k = LayananKategori.tambah(payload, f"/media/categories/{path.name}")
    except ValueError as exc:
        if path and path.exists():
            path.unlink(missing_ok=True)
        return jsonify(error=str(exc)), 422
    audit.catat("kategori_dibuat", "category", k.id, k.name, commit=True)
    return jsonify(message="Kategori ditambahkan.", kategori=LayananKategori.daftar()), 201


@admin_bp.put("/api/kategori/<int:kategori_id>")
@admin_required
def api_ubah_kategori(kategori_id: int):
    k = db.session.get(Category, kategori_id)
    if k is None:
        return jsonify(error="Kategori tidak ditemukan."), 404
    payload = request.form.to_dict() if request.mimetype == "multipart/form-data" else (request.get_json(silent=True) or {})
    foto = request.files.get("gambar")
    path = None
    try:
        image_url = None
        if foto and foto.filename:
            path = simpan_gambar_upload(foto, current_app.config["CATEGORY_UPLOAD_FOLDER"], current_app.config["CATEGORY_MAX_BYTES"])
            image_url = f"/media/categories/{path.name}"
        LayananKategori.ubah(k, payload, image_url=image_url)
    except ValueError as exc:
        db.session.rollback()
        if path and path.exists():
            path.unlink(missing_ok=True)
        return jsonify(error=str(exc)), 422
    audit.catat("kategori_diubah", "category", k.id, k.name, commit=True)
    return jsonify(message="Kategori diperbarui.", kategori=LayananKategori.daftar())


@admin_bp.delete("/api/kategori/<int:kategori_id>")
@admin_required
def api_hapus_kategori(kategori_id: int):
    k = db.session.get(Category, kategori_id)
    if k is None:
        return jsonify(error="Kategori tidak ditemukan."), 404
    nama = k.name
    hasil = LayananKategori.hapus(k)
    audit.catat(f"kategori_{hasil}", "category", kategori_id, nama, commit=True)
    pesan = "Kategori dihapus." if hasil == "dihapus" else "Kategori masih dipakai produk, jadi dinonaktifkan."
    return jsonify(message=pesan, hasil=hasil, kategori=LayananKategori.daftar())
