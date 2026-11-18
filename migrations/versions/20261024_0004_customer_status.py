"""Status akun customer: alasan status dan soft delete (non-destruktif).

Revision ID: 20261024_0004
Revises: 20261017_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_0004"
down_revision = "20261017_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("status_reason", sa.String(300), nullable=True))
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])


def downgrade():
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "status_reason")
