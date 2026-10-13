"""Service checkout. Logika lengkap dibuat pada Tahap 6."""


class LayananCheckout:
    """Class OOP yang nantinya menangani alur checkout customer."""

    def __init__(self, customer):
        self.customer = customer

    def buat_pesanan(self):
        """Membuat order berdasarkan isi keranjang customer."""
        raise NotImplementedError("Checkout dibuat pada Tahap 6")
