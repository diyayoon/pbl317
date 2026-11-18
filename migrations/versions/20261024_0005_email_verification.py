"""Verifikasi email: kolom is_verified dan tabel token (non-destruktif).

Akun yang sudah ada dianggap terverifikasi agar tidak terkunci; hanya akun baru yang wajib verifikasi.

Revision ID: 20261024_0005
Revises: 20261024_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_0005"
down_revision = "20261024_0004"
branch_labels = None
depends_on = None


def upgrade():
    # server_default true untuk baris lama; default model (False) berlaku untuk akun baru.
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "is_verified", server_default=sa.false())
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])


def downgrade():
    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "is_verified")
