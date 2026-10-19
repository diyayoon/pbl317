"""Keamanan sesi, moderasi ulasan, kategori aktif, audit log, rate limit.

Revision ID: 20261017_0003
Revises: 20261016_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261017_0003"
down_revision = "20261016_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("categories", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("reviews", sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("reviews", sa.Column("hidden_reason", sa.String(300), nullable=True))
    op.add_column("reviews", sa.Column("moderated_by", sa.Integer(), nullable=True))
    op.add_column("reviews", sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reviews", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_reviews_is_hidden", "reviews", ["is_hidden"])
    op.create_foreign_key("fk_reviews_moderated_by", "reviews", "users", ["moderated_by"], ["id"], ondelete="SET NULL")

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_email", sa.String(254), nullable=False, server_default=""),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False, server_default=""),
        sa.Column("target_id", sa.String(60), nullable=False, server_default=""),
        sa.Column("detail", sa.String(500), nullable=False, server_default=""),
        sa.Column("ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("key", sa.String(254), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rate_limit_lookup", "rate_limit_events", ["kind", "key", "created_at"])


def downgrade():
    op.drop_index("ix_rate_limit_lookup", table_name="rate_limit_events")
    op.drop_table("rate_limit_events")
    for name in ("ix_audit_logs_created_at", "ix_audit_logs_action", "ix_audit_logs_actor_id"):
        op.drop_index(name, table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_constraint("fk_reviews_moderated_by", "reviews", type_="foreignkey")
    op.drop_index("ix_reviews_is_hidden", table_name="reviews")
    for col in ("updated_at", "moderated_at", "moderated_by", "hidden_reason", "is_hidden"):
        op.drop_column("reviews", col)
    op.drop_column("categories", "is_active")
    op.drop_column("users", "auth_version")
