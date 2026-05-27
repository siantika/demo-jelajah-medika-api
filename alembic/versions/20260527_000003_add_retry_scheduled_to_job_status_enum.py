"""add RETRY_SCHEDULED to job_status_enum

Revision ID: 20260527_000003
Revises: 73e51f1297da
Create Date: 2026-05-27 00:00:03
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260527_000003"
down_revision = "73e51f1297da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_status_enum ADD VALUE IF NOT EXISTS 'RETRY_SCHEDULED'")


def downgrade() -> None:
    # PostgreSQL does not support dropping a single enum value safely.
    # Keeping no-op downgrade to avoid destructive enum recreation.
    pass
