"""Enforce unique user-role assignments

Revision ID: 003_user_role_unique
Revises: 002_procedure_centric_domain
Create Date: 2026-03-13
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_user_role_unique"
down_revision: Union[str, None] = "002_procedure_centric_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_user_role_assignments_user_id_role_id",
        "user_role_assignments",
        ["user_id", "role_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_user_role_assignments_user_id_role_id",
        "user_role_assignments",
        type_="unique",
    )
