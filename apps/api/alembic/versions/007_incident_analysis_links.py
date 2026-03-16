"""Link related incident matches to exact analysis runs

Revision ID: 007_incident_analysis_links
Revises: 006_proc_version_source_ai
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_incident_analysis_links"
down_revision: Union[str, None] = "006_proc_version_source_ai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incident_related_matches",
        sa.Column("related_analysis_run_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "incident_related_matches_related_analysis_run_id_fkey",
        "incident_related_matches",
        "incident_analysis_runs",
        ["related_analysis_run_id"],
        ["id"],
        ondelete="CASCADE",
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE incident_related_matches AS irm
            SET related_analysis_run_id = latest_run.id
            FROM (
                SELECT DISTINCT ON (incident_id) id, incident_id
                FROM incident_analysis_runs
                ORDER BY incident_id, created_at DESC, id DESC
            ) AS latest_run
            WHERE irm.related_incident_id = latest_run.incident_id
            """
        )
    )
    op.alter_column("incident_related_matches", "related_analysis_run_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint(
        "incident_related_matches_related_analysis_run_id_fkey",
        "incident_related_matches",
        type_="foreignkey",
    )
    op.drop_column("incident_related_matches", "related_analysis_run_id")
