"""Admin: kelola akun customer (daftar, detail, status, soft delete)."""
from __future__ import annotations
from flask import jsonify, render_template, request
from app.extensions import db
from app.services.pelanggan_admin_service import ErrorPelanggan, LayananPelangganAdmin
from . import admin_bp
from app.utils.decorators import admin_required


def _galat(exc: ErrorPelanggan):
    db.session.rollback()
    return jsonify(error=exc.pesan), exc.kode


@admin_bp.get("/pengguna")
@admin_required
def pengguna():
    return render_template("admin/users.html", pengguna_list=LayananPelangganAdmin().daftar())


@admin_bp.get("/api/pengguna")
@admin_required
def api_pengguna():
    return jsonify(LayananPelangganAdmin().daftar(request.args.get("q", ""), request.args.get("status", "")))


@admin_bp.get("/api/pengguna/<int:user_id>")
@admin_required
def api_detail_pengguna(user_id: int):
    try:
        return jsonify(LayananPelangganAdmin().detail(user_id))
    except ErrorPelanggan as exc:
        return _galat(exc)


@admin_bp.post("/api/pengguna/<int:user_id>/status")
@admin_required
def api_status_pengguna(user_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(LayananPelangganAdmin().ubah_status(user_id, str(data.get("aksi", "")), str(data.get("alasan", ""))))
    except ErrorPelanggan as exc:
        return _galat(exc)


@admin_bp.delete("/api/pengguna/<int:user_id>")
@admin_required
def api_hapus_pengguna(user_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(LayananPelangganAdmin().hapus_lunak(user_id, str(data.get("konfirmasi_email", "")), str(data.get("alasan", ""))))
    except ErrorPelanggan as exc:
        return _galat(exc)
