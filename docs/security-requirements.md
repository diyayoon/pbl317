# Security Requirements — Albis Antique

Dokumen ini adalah baseline SSDLC. Status backend masih **planned** kecuali kontrol frontend/struktur yang sudah ada.

| ID | Requirement | Acuan | Status |
|---|---|---|---|
| SR-01 | Password disimpan sebagai hash kuat; tidak pernah plaintext. | OWASP Authentication | Planned |
| SR-02 | Role admin/customer diputuskan server, bukan JavaScript. | Broken Access Control | Planned |
| SR-03 | Semua POST/PUT/DELETE memakai proteksi CSRF. | CSRF | Struktur Flask-WTF siap |
| SR-04 | Query database memakai ORM/parameterized query. | Injection | Planned |
| SR-05 | Total dan harga checkout dihitung ulang dari database di server. | Insecure Design | Planned |
| SR-06 | Order, alamat, review, dan resource user dicek kepemilikannya. | IDOR/BOLA | Planned |
| SR-07 | Upload avatar/produk/bukti bayar divalidasi ekstensi, ukuran, MIME/magic bytes, lalu diberi nama acak. | Unrestricted File Upload | Planned |
| SR-08 | File upload sensitif tidak dieksekusi dan idealnya disimpan di luar static/public root. | Web Shell / File Upload | Planned |
| SR-09 | Login diberi rate limiting dan pesan error generik. | Brute Force | Planned |
| SR-10 | Session memakai HttpOnly, SameSite, dan Secure pada production. | Session Security | Sebagian siap di config |
| SR-11 | Secret production wajib berasal dari environment, tidak di-commit. | Secrets Management | Planned sebelum deploy |
| SR-12 | Jinja autoescape dipertahankan dan data user tidak dipasang melalui `innerHTML`. | XSS | UI diarahkan aman |
| SR-13 | Dependency diperiksa dengan `pip-audit` dan source dengan `bandit`. | Vulnerable Components | Planned CI |
| SR-14 | Event penting dilog: login gagal, approval pembayaran, perubahan role, dan akses ditolak. | Logging & Monitoring | Planned |
| SR-15 | Production memakai HTTPS, debug mati, dan security headers. | Security Misconfiguration | Planned |

## Threat model minimum
Threat model STRIDE perlu dibuat untuk tiga alur paling berisiko: autentikasi, checkout/pembayaran, dan upload file. Mapping ATT&CK/CAPEC/CWE digunakan sebagai referensi ancaman dan pengujian, bukan sebagai pengganti kontrol aplikasi.
