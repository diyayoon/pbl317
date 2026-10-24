"""Kode verifikasi email (OTP): hash kode dan penghitung percobaan (non-destruktif).

Revision ID: 20261024_0007
Revises: 20261024_0006
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_0007"
down_revision = "20261024_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("email_verification_tokens", sa.Column("code_hash", sa.String(64), nullable=True))
    op.add_column("email_verification_tokens", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("email_verification_tokens", "attempts")
    op.drop_column("email_verification_tokens", "code_hash")
