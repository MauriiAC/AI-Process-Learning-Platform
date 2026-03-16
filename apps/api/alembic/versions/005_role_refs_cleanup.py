"""Clean remaining role string references

Revision ID: 005_role_refs_cleanup
Revises: 004_drop_user_role
Create Date: 2026-03-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_role_refs_cleanup"
down_revision: Union[str, None] = "004_drop_user_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("role_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=True),
    )
    op.drop_column("incidents", "role")
    op.drop_column("tasks", "role")


def downgrade() -> None:
    op.add_column("tasks", sa.Column("role", sa.String(length=100), nullable=True))
    op.add_column("incidents", sa.Column("role", sa.String(length=100), nullable=True))
    op.drop_column("incidents", "role_id")
