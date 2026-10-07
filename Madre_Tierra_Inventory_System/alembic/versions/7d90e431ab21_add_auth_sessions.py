"""Store revocable sessions for the single operator.

Revision ID: 7d90e431ab21
Revises: 6952ae074881
"""
from alembic import op
import sqlalchemy as sa

revision = "7d90e431ab21"
down_revision = "6952ae074881"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_session",
        sa.Column("token_hash", sa.String(64), primary_key=True, nullable=False),
        sa.Column("credentials_fingerprint", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auth_session_expires_at", "auth_session", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_session_expires_at", table_name="auth_session")
    op.drop_table("auth_session")
