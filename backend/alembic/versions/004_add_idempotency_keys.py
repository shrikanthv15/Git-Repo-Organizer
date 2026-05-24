"""Add idempotency_keys table

Revision ID: 004
Revises: 003
Create Date: 2026-05-24

E5 guardrails — dedup window for mutating endpoints. Same
``Idempotency-Key`` header from the same Bearer token within 24h
returns the previously-issued workflow_id instead of starting a new
workflow. See ``app/services/idempotency.py``.

The PK is composite (token_fingerprint, key, endpoint) so:
- Two different users can use the same key value
- Same user can use the same key value across different endpoints
- Only the (key, user, endpoint) triple dedups

``created_at`` is indexed for the 24h-window lookup query.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("token_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("workflow_id", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "token_fingerprint", "key", "endpoint",
            name="pk_idempotency_keys",
        ),
    )
    op.create_index(
        "ix_idempotency_keys_created_at",
        "idempotency_keys",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_created_at", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
