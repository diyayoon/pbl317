"""Persist free-text address submitted during registration.

Revision ID: 20261016_0002
Revises: 20261016_0001
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "20261016_0002"
down_revision = "20261016_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("alamat_registrasi", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("users", "alamat_registrasi")
