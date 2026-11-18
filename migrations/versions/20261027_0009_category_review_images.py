"""Foto tetap kategori dan lampiran foto ulasan.

Revision ID: 20261027_0009
Revises: 20261024_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20261027_0009"
down_revision = "20261024_0008"
branch_labels = None
depends_on = None

CATEGORY_IMAGES = {
    "timepiece": "/static/images/categories/jam-timepiece.jpg",
    "camera": "/static/images/categories/kamera-vintage.jpg",
    "porcelain": "/static/images/categories/porselen-keramik.jpg",
    "books": "/static/images/categories/buku-manuskrip.jpg",
    "jewelry": "/static/images/categories/perhiasan-antik.jpg",
    "music": "/static/images/categories/musik-vintage.jpg",
    "decor": "/static/images/categories/dekorasi-interior.jpg",
    "travel": "/static/images/categories/travel-collectibles.jpg",
}


def upgrade():
    op.add_column("categories", sa.Column("image_url", sa.String(length=500), nullable=True))
    op.add_column("reviews", sa.Column("image_path", sa.String(length=500), nullable=True))
    conn = op.get_bind()
    for slug, image in CATEGORY_IMAGES.items():
        conn.execute(
            sa.text("UPDATE categories SET image_url = :image WHERE slug = :slug AND (image_url IS NULL OR image_url = '')"),
            {"image": image, "slug": slug},
        )


def downgrade():
    op.drop_column("reviews", "image_path")
    op.drop_column("categories", "image_url")
