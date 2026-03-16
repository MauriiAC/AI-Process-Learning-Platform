"""Redesign incident analysis around runs and findings

Revision ID: 008_incident_findings
Revises: 007_incident_analysis_links
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_incident_findings"
down_revision: Union[str, None] = "007_incident_analysis_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("incident_related_matches")
    op.drop_table("incident_analysis_runs")
    op.drop_table("incident_procedure_hypotheses")

    op.create_table(
        "incident_analysis_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("analysis_summary", sa.Text(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "incident_analysis_findings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incident_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("finding_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "incident_related_matches",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incident_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_incident_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_analysis_run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incident_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("incident_related_matches")
    op.drop_table("incident_analysis_findings")
    op.drop_table("incident_analysis_runs")

    op.create_table(
        "incident_procedure_hypotheses",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "procedure_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedures.id"),
            nullable=True,
        ),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id"),
            nullable=True,
        ),
        sa.Column("task_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column(
            "training_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trainings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "incident_analysis_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("analysis_summary", sa.Text(), nullable=True),
        sa.Column(
            "confirmed_procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id"),
            nullable=True,
        ),
        sa.Column(
            "confirmed_training_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trainings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "incident_related_matches",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incident_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_incident_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_analysis_run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incident_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
