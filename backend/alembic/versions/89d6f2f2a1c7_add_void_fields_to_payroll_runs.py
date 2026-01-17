"""add void fields to payroll runs

Revision ID: 89d6f2f2a1c7
Revises: da7e2e928e54
Create Date: 2026-01-02 04:12:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "89d6f2f2a1c7"
down_revision = "da7e2e928e54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payroll_runs", sa.Column("void_reason", sa.String(length=255), nullable=True))
    op.add_column("payroll_runs", sa.Column("voided_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("payroll_runs", "voided_at")
    op.drop_column("payroll_runs", "void_reason")
