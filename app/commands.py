"""Perintah administratif eksplisit; tidak berjalan otomatis saat startup."""
import click
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash
from .extensions import db


def register_commands(app):
    @app.cli.command("db-check")
    def db_check():
        """Uji koneksi database dengan query read-only SELECT 1."""
        try:
            db.session.execute(text("SELECT 1"))
            click.echo("PASS: koneksi database berhasil (SELECT 1).")
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise click.ClickException(f"Koneksi database gagal: {exc.__class__.__name__}") from exc

    @app.cli.command("uji-email")
    @click.argument("tujuan")
    def uji_email(tujuan):
        """Periksa konfigurasi email lalu kirim satu email uji ke TUJUAN. Tidak menampilkan password."""
        import re
        from .utils.email import kirim_email, smtp_terkonfigurasi
        c = app.config
        masalah = []
        if not smtp_terkonfigurasi():
            masalah.append("MAIL_SERVER / MAIL_USERNAME / MAIL_PASSWORD / MAIL_FROM belum lengkap di .env.")
        if "example" in str(c.get("APP_BASE_URL") or "") or not c.get("APP_BASE_URL"):
            masalah.append("APP_BASE_URL masih kosong/placeholder: tautan di email akan menunjuk ke alamat yang salah.")
        if c.get("MAIL_SERVER") == "smtp.gmail.com" and not re.fullmatch(r"[a-z]{16}", str(c.get("MAIL_PASSWORD") or "").replace(" ", "")):
            masalah.append("MAIL_PASSWORD bukan format App Password Gmail (16 huruf kecil). Password akun biasa akan ditolak Gmail.")
        if c.get("MAIL_USERNAME") != c.get("MAIL_FROM"):
            masalah.append("MAIL_FROM sebaiknya sama dengan MAIL_USERNAME (Gmail mengganti pengirim dengan akun yang login).")
        if c.get("SESSION_COOKIE_SECURE") and str(c.get("APP_BASE_URL") or "").startswith("http://"):
            masalah.append("SESSION_COOKIE_SECURE=1 tetapi APP_BASE_URL memakai http://: browser bisa menolak cookie sesi (isi SESSION_COOKIE_SECURE=0 untuk uji lewat HTTP).")
        for m in masalah:
            click.echo(f"PERIKSA: {m}")
        try:
            with app.test_request_context():
                hasil = kirim_email(tujuan, "Uji email Albis Antique", "Jika Anda membaca ini, pengiriman email berhasil.")
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(f"Gagal: {exc.__class__.__name__}") from exc
        if hasil:
            click.echo(f"BERHASIL: email uji dikirim ke {tujuan}. Cek inbox dan folder spam.")
        else:
            click.echo("GAGAL: lihat baris 'Gagal mengirim email' di atas untuk jenis errornya "
                       "(SMTPAuthenticationError 535 = App Password salah / 2-Step belum aktif; gaierror = tidak ada internet/DNS).")
            raise SystemExit(1)

    @app.cli.command("uji-midtrans")
    def uji_midtrans():
        """Coba Server Key ke SANDBOX Midtrans dengan satu transaksi uji (tanpa uang). Tidak menampilkan kunci."""
        import secrets
        from .services import midtrans_service as ms
        if not ms.aktif():
            raise click.ClickException("MIDTRANS_SERVER_KEY belum diisi di .env.")
        if app.config.get("MIDTRANS_IS_PRODUCTION"):
            raise click.ClickException("MIDTRANS_IS_PRODUCTION=1: perintah uji ini hanya untuk sandbox. Ubah ke 0 dulu.")
        ref = f"UJI-{secrets.token_hex(4).upper()}"
        try:
            with app.test_request_context():
                status, hasil = ms._http("POST", f"{ms._basis()[0]}/snap/v1/transactions",
                                         {"transaction_details": {"order_id": ref, "gross_amount": 10000}})
        except ms.ErrorMidtrans as exc:
            raise click.ClickException(f"Tidak terhubung ke Midtrans: {exc.pesan}") from exc
        if status in (200, 201) and hasil.get("redirect_url"):
            click.echo(f"BERHASIL: kunci diterima server SANDBOX (transaksi uji {ref}, Rp10.000, tidak ditagihkan).")
        elif status == 401:
            click.echo("DITOLAK (401): kunci tidak dikenali server sandbox. Pastikan dashboard dalam mode Sandbox, salin Server Key "
                       "(bukan Client Key), tanpa spasi, atau kunci sudah di-Regenerate.")
            raise SystemExit(1)
        else:
            alasan = "; ".join(map(str, hasil.get("error_messages", [])))[:300] if isinstance(hasil, dict) else ""
            click.echo(f"GAGAL (HTTP {status}): {alasan}")
            raise SystemExit(1)

    @app.cli.command("init-dev-db")
    @click.option("--tanpa-produk", is_flag=True, help="Hanya kategori, tanpa koleksi pembuka.")
    @click.pass_context
    def init_dev_db(ctx, tanpa_produk):
        """Buat tabel + data awal di SQLite lokal (preview tanpa PostgreSQL)."""
        uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
        if not uri.startswith("sqlite") or app.config.get("APP_ENV") != "development":
            raise click.ClickException("Perintah ini hanya untuk SQLite dengan APP_ENV=development. Untuk PostgreSQL pakai: db upgrade.")
        db.create_all()
        ctx.invoke(seed_catalog, tanpa_produk=tanpa_produk)
        click.echo("Database lokal siap. Buat admin dengan: python -m flask --app run create-admin")

    @app.cli.command("seed-catalog")
    @click.option("--tanpa-produk", is_flag=True, help="Hanya tambahkan kategori, tanpa koleksi pembuka.")
    def seed_catalog(tanpa_produk):
        """Tambahkan kategori (dan koleksi pembuka bila katalog kosong)."""
        from .models import Category, Product, ProductImage
        from .seed_data import KATEGORI_AWAL, PRODUK_AWAL
        from .services.catalog_service import CatalogService
        try:
            for item in KATEGORI_AWAL:
                kategori = Category.query.filter_by(slug=item["slug"]).first()
                if kategori is None:
                    db.session.add(Category(name=item["nama"], slug=item["slug"], icon=item.get("ikon", "✧"), image_url=item.get("gambar", "")))
                elif not kategori.image_url:
                    kategori.image_url = item.get("gambar", "")
            db.session.flush()
            if not tanpa_produk and Product.query.count() == 0:
                by_slug = {c.slug: c for c in Category.query.all()}
                for item in PRODUK_AWAL:
                    product = Product(
                        category=by_slug.get(item.get("slug_kategori")), name=item["nama"],
                        slug=CatalogService.slug_unik(item["nama"]), description=item.get("deskripsi", ""),
                        price=item["harga"], stock=item.get("stok", 0), era=item.get("era", ""),
                        origin=item.get("asal", ""), material=item.get("material", ""),
                        condition=item.get("kondisi", "Good"), authenticity_status=item.get("autentikasi", "Not verified"),
                        image_alt=item.get("alt_gambar", item["nama"]), image_source=item.get("sumber_gambar", ""),
                    )
                    product.images.append(ProductImage(
                        image_url=item.get("gambar", ""), alt_text=item.get("alt_gambar", item["nama"]),
                        is_primary=True, position=0))
                    db.session.add(product)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise click.ClickException(f"Katalog awal gagal disiapkan ({exc.__class__.__name__}).") from exc
        click.echo("Selesai. Kategori yang belum ada ditambahkan; produk hanya ditambahkan jika katalog kosong.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True, help="Email akun administrator")
    @click.option("--nama", prompt="Nama administrator", help="Nama lengkap administrator")
    def create_admin(email, nama):
        """Buat admin internal (password diminta interaktif, minimal 16 karakter)."""
        from .models import User
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            raise click.ClickException("Email sudah terdaftar.")
        password = click.prompt("Password admin (minimal 16 karakter)", hide_input=True, confirmation_prompt=True)
        if len(password) < 16 or len(password) > 128:
            raise click.ClickException("Password harus terdiri dari 16–128 karakter.")
        user = User(email=email, nama=nama.strip(), role="admin", telepon="", password_hash=generate_password_hash(password))
        try:
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise click.ClickException(f"Admin gagal dibuat ({exc.__class__.__name__}).") from exc
        click.echo(f"Akun admin berhasil dibuat untuk {email}.")

    @app.cli.command("expire-orders")
    def expire_orders():
        """Batalkan pesanan yang melewati batas bayar dan kembalikan stoknya."""
        from .services.order_service import LayananPesanan
        click.echo(f"{LayananPesanan.kedaluwarsakan()} pesanan dikedaluwarsakan.")

    @app.cli.command("purge-security-events")
    @click.option("--hari", default=2, show_default=True)
    def purge_security_events(hari):
        """Hapus catatan percobaan login lama (tabel rate_limit_events)."""
        from .utils.ratelimit import pangkas_lama
        from .services.sesi_service import LayananSesi
        click.echo(f"{pangkas_lama(hari)} baris dihapus; {LayananSesi.pangkas(hari)} sesi lama dihapus.")
