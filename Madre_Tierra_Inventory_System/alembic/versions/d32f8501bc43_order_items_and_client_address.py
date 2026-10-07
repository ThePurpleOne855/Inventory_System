"""Create the missing order items table and add structured client addresses."""
from alembic import op
import sqlalchemy as sa

revision = "d32f8501bc43"
down_revision = "c21e7490ab32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orderproduct",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(), nullable=False),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_product_order_product"),
    )
    op.create_index("ix_orderproduct_order_id", "orderproduct", ["order_id"])
    op.create_index("ix_orderproduct_product_id", "orderproduct", ["product_id"])
    for field in ("city", "state", "country", "zipcode"):
        op.add_column("client", sa.Column(field, sa.String(), nullable=True))


def downgrade() -> None:
    for field in ("zipcode", "country", "state", "city"):
        op.drop_column("client", field)
    op.drop_table("orderproduct")
