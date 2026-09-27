"""Add user_sessions table

Revision ID: 005
Revises: 004
Create Date: 2026-09-27

PAN-9 introduced the UserSession model (server-side session carrying the
Fernet-encrypted GitHub token, referenced by the session_id HttpOnly
cookie) but never shipped a migration for it, so /auth/exchange and every
cookie-authenticated endpoint fail on a fresh database. This revision
creates the table to match app/db/models.py::UserSession.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("encrypted_github_token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("user_sessions")
