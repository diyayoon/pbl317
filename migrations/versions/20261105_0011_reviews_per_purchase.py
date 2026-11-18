"""Ulasan terikat ke item pesanan, sehingga pembelian berulang dapat diulas.

Revision ID: 20261105_0011
Revises: 20261105_0010
"""
from alembic import op
import sqlalchemy as sa

revision = "20261105_0011"
down_revision = "20261105_0010"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reviews") as batch:
        batch.add_column(sa.Column("order_item_id", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_review_user_product", type_="unique")
        batch.create_foreign_key(
            "fk_reviews_order_item_id_order_items",
            "order_items",
            ["order_item_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_unique_constraint("uq_reviews_order_item", ["order_item_id"])

    # Kaitkan ulasan lama ke satu item pembelian selesai yang paling baru.
    # Ulasan lama yang tidak memiliki pesanan selesai tetap tersimpan sebagai ulasan historis.
    op.execute(sa.text("""
        UPDATE reviews
        SET order_item_id = (
            SELECT oi.id
            FROM order_items AS oi
            JOIN orders AS o ON o.id = oi.order_id
            WHERE o.user_id = reviews.user_id
              AND o.status = 'Selesai'
              AND oi.product_id = reviews.product_id
            ORDER BY o.updated_at DESC, o.created_at DESC, oi.id DESC
            LIMIT 1
        )
        WHERE order_item_id IS NULL
    """))


def downgrade():
    # Downgrade hanya aman jika belum ada pembelian berulang yang menghasilkan
    # lebih dari satu ulasan untuk kombinasi customer dan produk yang sama.
    bind = op.get_bind()
    duplicate = bind.execute(sa.text("""
        SELECT 1 FROM reviews
        GROUP BY user_id, product_id
        HAVING COUNT(*) > 1
        LIMIT 1
    """)).first()
    if duplicate:
        raise RuntimeError(
            "Downgrade tidak dapat dilakukan: sudah ada beberapa ulasan untuk customer dan produk yang sama."
        )
    with op.batch_alter_table("reviews") as batch:
        batch.drop_constraint("uq_reviews_order_item", type_="unique")
        batch.drop_constraint("fk_reviews_order_item_id_order_items", type_="foreignkey")
        batch.drop_column("order_item_id")
        batch.create_unique_constraint("uq_review_user_product", ["user_id", "product_id"])
