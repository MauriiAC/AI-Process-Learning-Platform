"""Add incident semantic metadata

Revision ID: 013_incident_semantic_metadata
Revises: 012_operator_incident_resolution
Create Date: 2026-03-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_incident_semantic_metadata"
down_revision: Union[str, None] = "012_operator_incident_resolution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("incident_type", sa.String(length=50), nullable=False, server_default="other"),
    )
    op.add_column(
        "incidents",
        sa.Column("incident_category", sa.String(length=50), nullable=False, server_default="other"),
    )
    op.add_column(
        "incidents",
        sa.Column("incident_entities_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.alter_column("incidents", "incident_type", server_default=None)
    op.alter_column("incidents", "incident_category", server_default=None)


def downgrade() -> None:
    op.drop_column("incidents", "incident_entities_json")
    op.drop_column("incidents", "incident_category")
    op.drop_column("incidents", "incident_type")
