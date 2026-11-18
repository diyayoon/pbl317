"""Kolom payment gateway Midtrans pada payments (nullable, non-destruktif).

Revision ID: 20261024_0008
Revises: 20261024_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_0008"
down_revision = "20261024_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("snap_redirect_url", sa.String(500), nullable=True))
    op.add_column("payments", sa.Column("gateway_status", sa.String(30), nullable=True))
    op.add_column("payments", sa.Column("gateway_payment_type", sa.String(40), nullable=True))
    op.add_column("payments", sa.Column("gateway_transaction_id", sa.String(64), nullable=True))
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    for kolom in ("paid_at", "gateway_transaction_id", "gateway_payment_type", "gateway_status", "snap_redirect_url"):
        op.drop_column("payments", kolom)
