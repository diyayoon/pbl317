"""Permintaan refund Midtrans dan status konfirmasi gateway.

Revision ID: 20261105_0010
Revises: 20261027_0009
"""
from alembic import op
import sqlalchemy as sa

revision = "20261105_0010"
down_revision = "20261027_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "refund_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("amount", sa.Numeric(14, 0), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="Menunggu persetujuan"),
        sa.Column("refund_key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("gateway_status", sa.String(length=40), nullable=True),
        sa.Column("gateway_refund_id", sa.String(length=100), nullable=True),
        sa.Column("gateway_payment_type", sa.String(length=40), nullable=True),
        sa.Column("admin_note", sa.String(length=500), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_refund_requests_order_id", "refund_requests", ["order_id"])
    op.create_index("ix_refund_requests_user_id", "refund_requests", ["user_id"])
    op.create_index("ix_refund_requests_status", "refund_requests", ["status"])
    op.create_index("ix_refund_requests_status_created", "refund_requests", ["status", "requested_at"])
    op.create_index("ix_refund_requests_order", "refund_requests", ["order_id", "requested_at"])


def downgrade():
    op.drop_index("ix_refund_requests_order", table_name="refund_requests")
    op.drop_index("ix_refund_requests_status_created", table_name="refund_requests")
    op.drop_index("ix_refund_requests_status", table_name="refund_requests")
    op.drop_index("ix_refund_requests_user_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_order_id", table_name="refund_requests")
    op.drop_table("refund_requests")
