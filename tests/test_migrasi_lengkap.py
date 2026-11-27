
"""Pengujian kelengkapan dan perilaku migration database."""

import glob
import importlib.util
import os
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.extensions import db


NAMA_MIGRASI_STOCK = (
    "20261127_0014_idempotensi_pengembalian_stok.py"
)


def _identifier_ada(nama, sumber):
    """Cocokkan identifier dengan tanda kutip tunggal maupun ganda."""
    return f'"{nama}"' in sumber or f"'{nama}'" in sumber


def _muat_migrasi_stock():
    """Muat migration 0014 tanpa menjalankan seluruh rantai Alembic."""
    akar = Path(__file__).resolve().parents[1]
    lokasi = akar / "migrations" / "versions" / NAMA_MIGRASI_STOCK

    spec = importlib.util.spec_from_file_location(
        "migrasi_0014_stock_returned",
        lokasi,
    )

    assert spec is not None and spec.loader is not None

    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)

    return modul


def test_semua_tabel_dan_kolom_model_punya_migrasi(app):
    """Setiap tabel dan kolom model harus tercatat dalam source migration."""
    akar = os.path.dirname(os.path.dirname(__file__))

    file_migrasi = glob.glob(
        os.path.join(akar, "migrations", "versions", "*.py")
    )

    migrasi = ""

    for file in file_migrasi:
        with open(file, encoding="utf-8") as f:
            migrasi += f.read() + "\n"

    hilang = []

    for tabel in db.metadata.sorted_tables:
        if not _identifier_ada(tabel.name, migrasi):
            hilang.append(tabel.name)
            continue

        for kolom in tabel.columns:
            if not _identifier_ada(kolom.name, migrasi):
                hilang.append(f"{tabel.name}.{kolom.name}")

    assert not hilang, f"Belum ada migrasi untuk: {hilang}"


def test_model_order_memiliki_penanda_stock_returned(app):
    """Model Order harus memiliki penanda pengembalian stok."""
    from app.models import Order

    kolom = Order.__table__.columns.get("stock_returned")

    assert kolom is not None
    assert kolom.nullable is False
    assert kolom.default is not None
    assert kolom.default.arg is False
    assert kolom.server_default is not None


def test_migration_stock_returned_memiliki_revision_yang_benar():
    """Migration 0014 harus melanjutkan migration 0013."""
    migrasi = _muat_migrasi_stock()

    assert migrasi.revision == "20261127_0014"
    assert migrasi.down_revision == "20261124_0013"


def test_migration_stock_upgrade_downgrade_upgrade_menjaga_data():
    """
    Uji perilaku migration pada SQLite terisolasi.

    PostgreSQL 16 tetap divalidasi secara terpisah melalui CI.
    """
    migrasi = _muat_migrasi_stock()

    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as koneksi:
        # Membuat tabel minimal untuk menguji migration 0014.
        koneksi.execute(text("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                status VARCHAR(40) NOT NULL
            )
        """))

        # Data sintetis untuk menguji aturan backfill.
        koneksi.execute(text("""
            INSERT INTO orders (id, status)
            VALUES
                (1, 'Dibatalkan'),
                (2, 'Direfund'),
                (3, 'Menunggu pembayaran'),
                (4, 'Diproses')
        """))

        def jalankan(fungsi_migrasi):
            konteks = MigrationContext.configure(koneksi)

            with Operations.context(konteks):
                fungsi_migrasi()

        # 1. UPGRADE
        jalankan(migrasi.upgrade)

        kolom = {
            item["name"]: item
            for item in inspect(koneksi).get_columns("orders")
        }

        assert "stock_returned" in kolom
        assert kolom["stock_returned"]["nullable"] is False
        assert kolom["stock_returned"]["default"] is not None

        hasil = koneksi.execute(text("""
            SELECT id, status, stock_returned
            FROM orders
            ORDER BY id
        """)).mappings().all()

        assert len(hasil) == 4

        status_awal = {
            item["id"]: item["status"]
            for item in hasil
        }

        penanda_awal = {
            item["id"]: bool(item["stock_returned"])
            for item in hasil
        }

        assert status_awal == {
            1: "Dibatalkan",
            2: "Direfund",
            3: "Menunggu pembayaran",
            4: "Diproses",
        }

        assert penanda_awal == {
            1: True,
            2: True,
            3: False,
            4: False,
        }

        # Pastikan insert baru mendapatkan default FALSE.
        koneksi.execute(text("""
            INSERT INTO orders (id, status)
            VALUES (5, 'Menunggu pembayaran')
        """))

        nilai_default = koneksi.execute(text("""
            SELECT stock_returned
            FROM orders
            WHERE id = 5
        """)).scalar_one()

        assert bool(nilai_default) is False

        # 2. DOWNGRADE
        jalankan(migrasi.downgrade)

        kolom_setelah_downgrade = {
            item["name"]
            for item in inspect(koneksi).get_columns("orders")
        }

        assert "stock_returned" not in kolom_setelah_downgrade

        data_setelah_downgrade = koneksi.execute(text("""
            SELECT id, status
            FROM orders
            ORDER BY id
        """)).mappings().all()

        assert len(data_setelah_downgrade) == 5
        assert {
            item["id"]: item["status"]
            for item in data_setelah_downgrade
        } == {
            1: "Dibatalkan",
            2: "Direfund",
            3: "Menunggu pembayaran",
            4: "Diproses",
            5: "Menunggu pembayaran",
        }

        # 3. UPGRADE ULANG
        jalankan(migrasi.upgrade)

        kolom_setelah_upgrade_ulang = {
            item["name"]
            for item in inspect(koneksi).get_columns("orders")
        }

        assert "stock_returned" in kolom_setelah_upgrade_ulang

        hasil_akhir = koneksi.execute(text("""
            SELECT id, status, stock_returned
            FROM orders
            ORDER BY id
        """)).mappings().all()

        assert len(hasil_akhir) == 5

        penanda_akhir = {
            item["id"]: bool(item["stock_returned"])
            for item in hasil_akhir
        }

        assert penanda_akhir == {
            1: True,
            2: True,
            3: False,
            4: False,
            5: False,
        }
