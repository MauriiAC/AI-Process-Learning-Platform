"""Add operator incident resolution fields

Revision ID: 012_operator_incident_resolution
Revises: 011_user_procedure_read_tracking
Create Date: 2026-03-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_operator_incident_resolution"
down_revision: Union[str, None] = "011_user_procedure_read_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("operator_comment", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("operator_resolution_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("incidents", sa.Column("operator_resolution_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("operator_selected_procedure_version_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("operator_selected_related_run_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "incidents_operator_resolution_by_fkey",
        "incidents",
        "users",
        ["operator_resolution_by"],
        ["id"],
    )
    op.create_foreign_key(
        "incidents_operator_selected_procedure_version_id_fkey",
        "incidents",
        "procedure_versions",
        ["operator_selected_procedure_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "incidents_operator_selected_related_run_id_fkey",
        "incidents",
        "incident_analysis_runs",
        ["operator_selected_related_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("incidents_operator_selected_related_run_id_fkey", "incidents", type_="foreignkey")
    op.drop_constraint("incidents_operator_selected_procedure_version_id_fkey", "incidents", type_="foreignkey")
    op.drop_constraint("incidents_operator_resolution_by_fkey", "incidents", type_="foreignkey")
    op.drop_column("incidents", "operator_selected_related_run_id")
    op.drop_column("incidents", "operator_selected_procedure_version_id")
    op.drop_column("incidents", "operator_resolution_at")
    op.drop_column("incidents", "operator_resolution_by")
    op.drop_column("incidents", "operator_comment")
