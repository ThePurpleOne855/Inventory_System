"""Add an optional address to client profiles."""
from alembic import op
import sqlalchemy as sa

revision = "c21e7490ab32"
down_revision = "7d90e431ab21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("client", sa.Column("address", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("client", "address")
