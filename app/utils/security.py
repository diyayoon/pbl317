"""Utilitas keamanan dan pengecekan kepemilikan data (anti-IDOR).

Albis Antique adalah single-store: tidak ada seller/toko. Resource milik user
(pesanan, alamat, ulasan, keranjang) hanya boleh diakses pemiliknya atau admin.
"""

from flask import abort


def pastikan_pemilik(user, pemilik_id: int) -> None:
    """Menolak akses (403) jika resource bukan milik user dan user bukan admin."""
    if user.role == "admin":
        return
    if str(user.id) != str(pemilik_id):
        abort(403)
