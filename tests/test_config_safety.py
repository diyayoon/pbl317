import pytest

from app import buat_app
from app.config import ProductionConfig


def test_production_menolak_secret_lemah(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "pendek")
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", "postgresql+psycopg://u:p@db/albis_db")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        buat_app(ProductionConfig)


def test_production_menolak_tanpa_database_url(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "x" * 40)
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", None)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        buat_app(ProductionConfig)


def test_hanya_postgresql_didukung(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "x" * 40)
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///x.db")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        buat_app(ProductionConfig)
