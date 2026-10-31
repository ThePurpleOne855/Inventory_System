"""Store order totals as exact money, keep cancelled orders, record client source.

Revision ID: e43a9612cd54
Revises: d32f8501bc43
"""
from alembic import op
import sqlalchemy as sa

revision = "e43a9612cd54"
down_revision = "d32f8501bc43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode lets SQLite (used by the tests) rebuild the table; Postgres alters in place.
    with op.batch_alter_table("orders") as batch:
        batch.alter_column(
            "total",
            type_=sa.Numeric(10, 2),
            existing_type=sa.Float(),
            existing_nullable=False,
            postgresql_using="round(total::numeric, 2)",
        )
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_orders_created_at", ["created_at"])
    op.add_column("client", sa.Column("source", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("client", "source")
    with op.batch_alter_table("orders") as batch:
        batch.drop_index("ix_orders_created_at")
        batch.drop_column("cancelled_at")
        batch.alter_column(
            "total",
            type_=sa.Float(),
            existing_type=sa.Numeric(10, 2),
            existing_nullable=False,
        )
