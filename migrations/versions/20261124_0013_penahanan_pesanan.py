"""Penahanan pesanan bernilai tidak wajar (anti-penipuan): kolom review pada orders.

Non-destruktif dan idempoten. Pesanan lama otomatis review_required = false.

Revision ID: 20261124_0013
Revises: 20261123_0012
"""
from alembic import op
import sqlalchemy as sa

revision = "20261124_0013"
down_revision = "d6e4584a4f85"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    ada = {c["name"] for c in sa.inspect(bind).get_columns("orders")}
    with op.batch_alter_table("orders") as batch:
        if "review_required" not in ada:
            batch.add_column(sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "review_reason" not in ada:
            batch.add_column(sa.Column("review_reason", sa.String(300), nullable=True))
        if "review_verified_by" not in ada:
            batch.add_column(sa.Column("review_verified_by", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_orders_review_verified_by_users", "users", ["review_verified_by"], ["id"], ondelete="SET NULL")
        if "review_verified_at" not in ada:
            batch.add_column(sa.Column("review_verified_at", sa.DateTime(timezone=True), nullable=True))
    indeks = {i["name"] for i in sa.inspect(bind).get_indexes("orders")}
    if "ix_orders_review_required" not in indeks:
        op.create_index("ix_orders_review_required", "orders", ["review_required"])


def downgrade():
    op.drop_index("ix_orders_review_required", table_name="orders")
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("fk_orders_review_verified_by_users", type_="foreignkey")
        batch.drop_column("review_verified_at")
        batch.drop_column("review_verified_by")
        batch.drop_column("review_reason")
        batch.drop_column("review_required")
