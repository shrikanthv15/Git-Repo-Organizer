"""Add status and last_gardener_run_at columns to analysis_results

Revision ID: 003
Revises: 002
Create Date: 2026-02-08

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_results",
        sa.Column("status", sa.String(), nullable=False, server_default="idle"),
    )
    op.add_column(
        "analysis_results",
        sa.Column("last_gardener_run_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_results", "last_gardener_run_at")
    op.drop_column("analysis_results", "status")
