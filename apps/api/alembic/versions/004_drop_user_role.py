"""Drop legacy users.role column

Revision ID: 004_drop_user_role
Revises: 003_user_role_unique
Create Date: 2026-03-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_drop_user_role"
down_revision: Union[str, None] = "003_user_role_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "role")


def downgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=100), nullable=True, server_default="employee"))
