# Pembagian kerja & kepemilikan file

Satu file = satu pemilik, jadi tidak ada file yang diedit dua orang (tidak bentrok saat merge).

Urutan merge ke branch `integrasi`: **Tiano → Arga → Intan → Fiony → Diya** (Fiony dan backend katalog Diya boleh bergantian setelah Intan; frontend Diya terakhir). `main` diisi dari `integrasi` setelah `pytest` hijau.

Alasan urutan (diperiksa dari impor antar-file): Arga butuh Tiano; Intan butuh Tiano dan Arga; Fiony butuh Tiano, Arga, dan Intan (`order_service` dipakai checkout dan dashboard); backend katalog Diya butuh Tiano, Arga, dan Intan (`review_service` dipakai halaman produk); frontend Diya butuh semua endpoint backend.


## Diya (frontend penuh + backend katalog + pemegang main)

**Frontend:** seluruh `app/templates/**` dan `app/static/**` (css, js, gambar, aset) — 76 file.

**Backend (katalog):**
- `app/blueprints/main/routes.py`
- `app/blueprints/admin/produk.py`
- `app/services/catalog_service.py`
- `app/services/category_service.py`


## Tiano (fondasi & database)

- `app/__init__.py`
- `app/blueprints/.gitkeep`
- `app/blueprints/__init__.py`
- `app/blueprints/admin/__init__.py`
- `app/blueprints/auth/__init__.py`
- `app/blueprints/customer/__init__.py`
- `app/blueprints/main/__init__.py`
- `app/commands.py`
- `app/config.py`
- `app/extensions.py`
- `app/models/.gitkeep`
- `app/models/__init__.py`
- `app/models/catalog.py`
- `app/models/commerce.py`
- `app/models/security.py`
- `app/models/user.py`
- `app/security.py`
- `app/seed_data.py`
- `app/services/.gitkeep`
- `app/utils/.gitkeep`
- `app/utils/network.py`
- `app/utils/uploads.py`
- `database/01_schema.sql`
- `database/02_data_awal.sql`
- `database/README.md`
- `migrations/README`
- `migrations/alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/20261016_0001_initial_schema.py`
- `migrations/versions/20261016_0002_registration_address.py`
- `migrations/versions/20261017_0003_security_reviews_categories.py`
- `pytest.ini`
- `run.py`
- `tests/conftest.py`
- `tests/test_config_safety.py`

## Arga (ketua: auth, keamanan, infra)

- `.dockerignore`
- `.env.example`
- `.gitignore`
- `Dockerfile`
- `README.md`
- `app/blueprints/admin/keamanan.py`
- `app/blueprints/auth/routes.py`
- `app/blueprints/customer/keamanan.py`
- `app/services/account_service.py`
- `app/utils/audit.py`
- `app/utils/decorators.py`
- `app/utils/ratelimit.py`
- `app/utils/validasi.py`
- `docker-compose.local.yml`
- `docker-compose.yml`
- `docs/KEAMANAN-OWASP-MITRE.md`
- `docs/PANDUAN-DEPLOY.md`
- `docs/image-sources.md`
- `nginx/Dockerfile`
- `nginx/default.conf`
- `nginx/proxy_params.conf`
- `requirements-dev.txt`
- `requirements.txt`
- `tests/test_security.py`

## Fiony (keranjang, checkout, profil, alamat)

- `app/blueprints/customer/checkout.py`
- `app/blueprints/customer/keranjang.py`
- `app/blueprints/customer/profil.py`
- `app/services/checkout_service.py`
- `app/services/customer_service.py`

## Intan (pesanan, pembayaran, ulasan, laporan)

- `app/blueprints/admin/laporan.py`
- `app/blueprints/admin/pesanan.py`
- `app/blueprints/customer/pesanan.py`
- `app/services/order_service.py`
- `app/services/payment_service.py`
- `app/services/report_service.py`
- `app/services/review_service.py`
- `tests/test_shop_flow.py`


## Aturan
- Edit hanya file milikmu. Butuh perubahan di file orang lain? Minta pemiliknya atau buka PR kecil terpisah.
- Jangan push: `.env`, `instance/`, `venv/`, `__pycache__/`.
- Commit atas nama orang yang menulisnya; `Co-authored-by` hanya untuk kerja bareng yang benar-benar terjadi.

