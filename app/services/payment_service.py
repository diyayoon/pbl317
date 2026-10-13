"""Service pembayaran. Logika lengkap dibuat pada Tahap 6."""


class LayananPembayaran:
    """Class OOP untuk alur bukti pembayaran."""

    def __init__(self, customer):
        self.customer = customer

    def simpan_bukti(self, order, file):
        """Menyimpan bukti pembayaran setelah validasi keamanan."""
        raise NotImplementedError("Pembayaran dibuat pada Tahap 6")
