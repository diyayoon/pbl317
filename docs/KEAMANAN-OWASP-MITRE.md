# Kontrol keamanan (OWASP Top 10:2025 · MITRE ATT&CK)

| OWASP | Risiko | Kontrol di kode | Teknik MITRE yang dipersempit |
|---|---|---|---|
| A01 Broken Access Control | Akses data/aksi pengguna lain | `role_required` di seluruh route admin/customer; semua query pesanan/alamat/keranjang difilter `user_id`; bukti bayar dilayani lewat **ID** dengan cek pemilik/admin; customer tak bisa mendaftar sebagai admin | T1078 Valid Accounts, T1190 Exploit Public-Facing App |
| A02 Security Misconfiguration | Header/cookie/konfigurasi lemah | CSP ketat (`script-src 'self'`, tanpa inline), X-Frame-Options, nosniff, Referrer/Permissions-Policy, HSTS, cookie HttpOnly+Secure+SameSite, `no-store` untuk halaman privat, nginx `server_tokens off`, produksi menolak start tanpa SECRET_KEY kuat/DATABASE_URL | T1190 |
| A03 Software Supply Chain | Dependensi tidak terkendali | `requirements.txt` dipatok persis; `pip-audit` bersih; image base tetap | T1195 Supply Chain Compromise |
| A04 Cryptographic Failures | Password/rahasia lemah | Hash scrypt (Werkzeug), SECRET_KEY min. 32 karakter, rahasia hanya dari environment, password min. 16 karakter | T1110, T1552 |
| A05 Injection | SQLi/XSS | Hanya ORM/parameter; LIKE di-escape; Jinja autoescape; JS memakai `textContent`; CSP memblokir skrip inline; unggahan diverifikasi signature (bukan ekstensi saja) | T1059, T1190 |
| A06 Insecure Design | Penyalahgunaan alur bisnis | Harga/total/stok dihitung & dikunci di server (`SELECT … FOR UPDATE`), transisi status dibatasi, maks. 5 pesanan terbuka, kedaluwarsa otomatis, ulasan hanya dari pembeli pesanan Selesai, tolak pembayaran wajib alasan | T1565 Data Manipulation |
| A07 Authentication Failures | Brute force, sesi dicuri | Batas 5 gagal/15 menit per email + per IP (database, aman multi-worker), login tiruan-hash anti-enumerasi, `session.clear()` saat login, ganti password mencabut semua sesi lain (`auth_version`), sesi 8 jam, `next` hanya path internal, nginx `limit_req` | T1110 Brute Force, T1550 |
| A08 Integrity Failures | Data/berkas dimanipulasi | CSRF token pada semua POST/PUT/PATCH/DELETE; foto/bukti dicek signature & ukuran; avatar divalidasi base64+signature | T1204, T1036 Masquerading |
| A09 Logging & Alerting | Serangan tak terlihat | Tabel `audit_logs` (login, perubahan produk/kategori/status/pembayaran/moderasi) + halaman `/admin/audit`; password tak pernah dicatat | T1070 (deteksi), T1078 |
| A10 Mishandling Exceptional Conditions | Error bocor / gagal terbuka | Handler global: JSON/HTML generik, rollback DB, tanpa stack trace; API balas 401 JSON saat sesi habis; transaksi atomik + rollback | T1499 DoS (dampak) |

## Cara menguji
```bash
python -m pytest -q                      # 25 tes otomatis
pip-audit -r requirements.txt            # kerentanan dependensi
bandit -q -r app -ll                     # analisis statis
```
Uji manual yang disarankan: 6× login salah (harus 429), buka `/customer/api/cart` tanpa login (401 JSON),
buka bukti bayar milik orang lain (403), ubah `?next=//evil.com` pada login (tetap internal).

## Batas yang perlu diketahui
- Pemulihan password lewat email belum ada (butuh layanan email); admin dapat membantu lewat CLI.
- Pembayaran manual (transfer + bukti); belum ada payment gateway.
- WAF/firewall/VLAN/DMZ ditangani tim jaringan (di luar aplikasi).
