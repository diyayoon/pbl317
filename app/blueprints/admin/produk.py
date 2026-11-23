"""Admin: produk dan kategori. (pemilik: Fiony)"""
from __future__ import annotations
from pathlib import Path
from flask import current_app, jsonify, render_template, request
from app.extensions import db
from app.models import Category
from app.services.catalog_service import CatalogService
from app.services.category_service import LayananKategori
from app.utils import audit
from app.utils.uploads import simpan_gambar_upload, simpan_dokumen_sertifikat
from . import admin_bp
from app.utils.decorators import admin_required

PRODUCT_MAX_BYTES = 2 * 1024 * 1024
PRODUCT_MAX_IMAGES = 5

class KesalahanUploadProduk(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field

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

def _hapus_file_sertifikat(path: str | Path | None) -> None:
    """Hapus sertifikat hanya jika berada di folder penyimpanan privat."""
    if not path:
        return

    base = Path(
        current_app.config["PRODUCT_CERTIFICATE_UPLOAD_FOLDER"]
    ).resolve()
    target = Path(path).resolve()

    if base in target.parents and target.is_file():
        try:
            target.unlink()
        except OSError:
            current_app.logger.warning(
                "Gagal menghapus sertifikat produk %s",
                target.name,
            )


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
    """Baca data produk, multi-image, dan sertifikat PDF."""

    if request.mimetype != "multipart/form-data":
        payload = request.get_json(silent=True)

        if isinstance(payload, dict):
            payload = dict(payload)

            if payload.get("gambar"):
                raise KesalahanUploadProduk(
                    "gambar",
                    "Foto produk harus diunggah sebagai berkas multipart/form-data.",
                )

            if payload.get("sertifikat"):
                raise KesalahanUploadProduk(
                    "sertifikat",
                    "Sertifikat harus diunggah sebagai berkas multipart/form-data.",
                )

            payload.pop("gambar", None)
            payload.pop("sertifikat", None)

        return payload, [], None, None, None, []

    payload = request.form.to_dict()
    payload.pop("gambar", None)
    payload.pop("sertifikat", None)
    payload.pop("foto_utama_index", None)
    payload.pop("hapus_gambar_ids", None)

    # Ambil seluruh gambar, bukan hanya gambar pertama.
    foto_files = [
        foto for foto in request.files.getlist("gambar")
        if foto and foto.filename
    ]

    # Validasi jumlah sebelum menyimpan file apa pun.
    if len(foto_files) > PRODUCT_MAX_IMAGES:
        raise KesalahanUploadProduk(
            "gambar",
            f"Maksimal 5 foto produk dapat diunggah.",
        )

    # Indeks foto utama merujuk pada urutan foto yang baru diunggah.
    primary_raw = (request.form.get("foto_utama_index") or "").strip()
    primary_index = None

    if primary_raw:
        try:
            primary_index = int(primary_raw)
        except ValueError as exc:
            raise KesalahanUploadProduk(
                "gambar",
                "Pilihan foto utama tidak valid.",
            ) from exc

        if primary_index < 0 or primary_index >= len(foto_files):
            raise KesalahanUploadProduk(
                "gambar",
                "Pilihan foto utama tidak tersedia.",
            )

    # Ambil ID gambar lama yang diminta untuk dihapus.
    delete_ids = []

    for raw_id in request.form.getlist("hapus_gambar_ids"):
        raw_id = raw_id.strip()
        if not raw_id:
            continue

        try:
            image_id = int(raw_id)
        except ValueError as exc:
            raise KesalahanUploadProduk(
                "gambar",
                "ID gambar yang ingin dihapus tidak valid.",
            ) from exc

        if image_id <= 0:
            raise KesalahanUploadProduk(
                "gambar",
                "ID gambar yang ingin dihapus tidak valid.",
            )

        delete_ids.append(image_id)

    if len(delete_ids) != len(set(delete_ids)):
        raise KesalahanUploadProduk(
            "gambar",
            "Daftar gambar yang dihapus mengandung ID duplikat.",
        )

    sertifikat = request.files.get("sertifikat")

    path_gambar = []
    path_sertifikat = None
    nama_sertifikat = None
    field = "gambar"

    try:
        batas_gambar = current_app.config.get(
            "PRODUCT_MAX_BYTES",
            PRODUCT_MAX_BYTES,
        )

        # Simpan seluruh foto dengan validasi yang sudah tersedia.
        for foto in foto_files:
            path = simpan_gambar_upload(
                foto,
                current_app.config["PRODUCT_UPLOAD_FOLDER"],
                batas_gambar,
            )
            path_gambar.append(path)

        # Sertifikat tetap diproses secara terpisah dan privat.
        field = "sertifikat"

        if sertifikat and sertifikat.filename:
            nama_sertifikat = sertifikat.filename

            path_sertifikat = simpan_dokumen_sertifikat(
                sertifikat,
                current_app.config["PRODUCT_CERTIFICATE_UPLOAD_FOLDER"],
                current_app.config["PRODUCT_CERTIFICATE_MAX_BYTES"],
            )

    except ValueError as exc:
        for path in path_gambar:
            _hapus_upload_sementara(path)

        _hapus_upload_sementara(path_sertifikat)

        raise KesalahanUploadProduk(field, str(exc)) from exc

    except Exception:
        for path in path_gambar:
            _hapus_upload_sementara(path)

        _hapus_upload_sementara(path_sertifikat)
        raise

    return (
        payload,
        path_gambar,
        path_sertifikat,
        nama_sertifikat,
        primary_index,
        delete_ids,
    )

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
        (
            payload,
            gambar_baru,
            sertifikat_baru,
            nama_sertifikat,
            primary_index,
            delete_ids,
        ) = _baca_payload_produk()
    except KesalahanUploadProduk as exc:
        return jsonify(
            error=str(exc),
            errors={exc.field: str(exc)},
        ), 422

    # Pembersihan file upload jika proses gagal.
    def bersihkan_upload():
        for path in gambar_baru:
            _hapus_upload_sementara(path)
        _hapus_upload_sementara(sertifikat_baru)

    # Pada pembuatan produk belum ada gambar lama yang bisa dihapus.
    if delete_ids:
        bersihkan_upload()
        return jsonify(
            error="Tidak dapat menghapus gambar pada produk baru.",
            errors={"hapus_gambar_ids": "ID gambar tidak valid."},
        ), 422

    image_urls = [
        f"/media/products/{path.name}"
        for path in gambar_baru
    ]

    try:
        product, errors = CatalogService.create_product(
            payload,
            image_url=image_urls[0] if image_urls else "",
            image_urls=image_urls,
            primary_image_index=primary_index,
            certificate_path=(
                str(sertifikat_baru.resolve())
                if sertifikat_baru else None
            ),
            certificate_original_filename=nama_sertifikat,
        )
    except Exception:
        bersihkan_upload()
        raise

    if errors:
        bersihkan_upload()
        return jsonify(
            error="Periksa kembali data produk.",
            errors=errors,
        ), 422

    audit.catat(
        "produk_dibuat",
        "product",
        product.id,
        product.name,
        commit=True,
    )

    return jsonify(
        message="Produk berhasil disimpan.",
        product=product.to_dict(),
        products=CatalogService.list_products(active_only=False),
    ), 201

@admin_bp.put("/api/produk/<int:produk_id>")
@admin_required
def api_ubah_produk(produk_id: int):
    existing = CatalogService.get_product(
        produk_id,
        active_only=False,
    )

    if existing is None:
        return jsonify(error="Produk tidak ditemukan."), 404

    harga_lama = existing.harga
    sertifikat_lama = existing.certificate_path

    # Simpan ID dan URL gambar lama sebelum perubahan database.
    gambar_lama = {
        image.id: image.image_url
        for image in existing.images
    }

    try:
        (
            payload,
            gambar_baru,
            sertifikat_baru,
            nama_sertifikat,
            primary_index,
            delete_ids,
        ) = _baca_payload_produk()
    except KesalahanUploadProduk as exc:
        return jsonify(
            error=str(exc),
            errors={exc.field: str(exc)},
        ), 422

    def bersihkan_upload():
        for path in gambar_baru:
            _hapus_upload_sementara(path)
        _hapus_upload_sementara(sertifikat_baru)

    # Pastikan ID gambar yang akan dihapus memang milik produk ini.
    delete_ids = set(delete_ids or [])
    id_gambar_tidak_valid = delete_ids - set(gambar_lama.keys())

    if id_gambar_tidak_valid:
        bersihkan_upload()
        return jsonify(
            error="Terdapat gambar yang tidak valid untuk dihapus.",
            errors={
                "hapus_gambar_ids": "ID gambar tidak ditemukan pada produk ini."
            },
        ), 422

    image_urls = [
        f"/media/products/{path.name}"
        for path in gambar_baru
    ]

    try:
        product, errors = CatalogService.update_product(
            existing,
            payload,
            image_url=image_urls[0] if image_urls else "",
            image_urls=image_urls,
            primary_image_index=primary_index,
            delete_image_ids=sorted(delete_ids),
            certificate_path=(
                str(sertifikat_baru.resolve())
                if sertifikat_baru else None
            ),
            certificate_original_filename=nama_sertifikat,
        )
    except Exception:
        bersihkan_upload()
        raise

    if errors:
        bersihkan_upload()
        return jsonify(
            error="Periksa kembali data produk.",
            errors=errors,
        ), 422

    # Hapus file fisik hanya setelah perubahan database berhasil.
    for image_id in delete_ids:
        _hapus_file_produk(gambar_lama.get(image_id))

    # Hapus sertifikat lama hanya jika sertifikat baru berhasil disimpan.
    if sertifikat_baru and sertifikat_lama:
        if Path(sertifikat_lama).resolve() != sertifikat_baru.resolve():
            _hapus_file_sertifikat(sertifikat_lama)

    audit.catat(
        "produk_diubah",
        "product",
        product.id,
        f"{product.name}; harga {harga_lama}->{product.harga}",
        commit=True,
    )

    return jsonify(
        message="Perubahan produk tersimpan.",
        product=product.to_dict(),
        products=CatalogService.list_products(active_only=False),
    )

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
