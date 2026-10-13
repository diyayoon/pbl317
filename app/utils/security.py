"""Utilitas keamanan dan pengecekan kepemilikan data."""

from flask import abort


def pastikan_pemilik_toko(user, store_id: int) -> None:
    """Menolak akses seller jika toko bukan miliknya (anti-IDOR)."""
    if user.role != "seller" or user.store_id != store_id:
        abort(403)
