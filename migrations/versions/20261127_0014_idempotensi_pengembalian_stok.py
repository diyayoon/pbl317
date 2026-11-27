"""Penanda idempotensi pengembalian stok pesanan."""

from alembic import op
import sqlalchemy as sa

revision = "20261127_0014"
down_revision = "20261124_0013"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    kolom = {
        c["name"]
        for c in sa.inspect(bind).get_columns("orders")
    }

    if "stock_returned" not in kolom:
        op.add_column(
            "orders",
            sa.Column(
                "stock_returned",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # Pesanan terminal pada alur aplikasi lama sudah melewati
    # proses pengembalian stok sebelum statusnya disimpan.
    op.execute(
        sa.text("""
            UPDATE orders
            SET stock_returned = TRUE
            WHERE status IN ('Dibatalkan', 'Direfund')
        """)
    )


def downgrade():
    bind = op.get_bind()

    kolom = {
        c["name"]
        for c in sa.inspect(bind).get_columns("orders")
    }

    if "stock_returned" in kolom:
        op.drop_column("orders", "stock_returned")
