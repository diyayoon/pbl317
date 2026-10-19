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
                if Category.query.filter_by(slug=item["slug"]).first() is None:
                    db.session.add(Category(name=item["nama"], slug=item["slug"], icon=item.get("ikon", "✧")))
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
        click.echo(f"{pangkas_lama(hari)} baris dihapus.")
