"""Penjaga: setiap tabel/kolom model harus muncul di migrasi
(tes lain memakai create_all sehingga tidak menangkapnya).
"""

import glob
import os

from app.extensions import db


def _identifier_ada(nama, sumber):
    """Cocokkan identifier dengan tanda kutip tunggal maupun ganda."""
    return f'"{nama}"' in sumber or f"'{nama}'" in sumber


def test_semua_tabel_dan_kolom_model_punya_migrasi(app):
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