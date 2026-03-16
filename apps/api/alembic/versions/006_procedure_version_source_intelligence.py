"""Move source intelligence artifacts to procedure versions

Revision ID: 006_proc_version_source_ai
Revises: 005_version_owned_training
Create Date: 2026-03-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "006_proc_version_source_ai"
down_revision: Union[str, None] = "005_version_owned_training"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "procedure_versions",
        sa.Column("source_processing_status", sa.String(length=50), nullable=False, server_default="pending"),
    )
    op.add_column("procedure_versions", sa.Column("source_processing_error", sa.Text(), nullable=True))
    op.add_column("procedure_versions", sa.Column("source_processed_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("procedure_versions", "source_processing_status", server_default=None)

    op.create_table(
        "procedure_version_transcripts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("transcript_raw", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "procedure_version_chunks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=True),
    )

    op.create_table(
        "procedure_version_structure",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("structure_json", sa.dialects.postgresql.JSONB(), nullable=False),
    )

    op.drop_table("video_frames")
    op.create_table(
        "video_frames",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
    )

    op.drop_table("semantic_segments")
    op.create_table(
        "semantic_segments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text_fused", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=True),
    )

    op.drop_table("training_chunks")
    op.drop_table("training_transcripts")

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
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("incident_related_matches")
    op.drop_table("incident_analysis_runs")

    op.create_table(
        "training_transcripts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "training_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trainings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("transcript_raw", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "training_chunks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "training_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trainings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=True),
    )

    op.drop_table("semantic_segments")
    op.create_table(
        "semantic_segments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "training_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trainings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text_fused", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(3072), nullable=True),
    )

    op.drop_table("video_frames")
    op.create_table(
        "video_frames",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "training_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trainings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
    )

    op.drop_table("procedure_version_structure")
    op.drop_table("procedure_version_chunks")
    op.drop_table("procedure_version_transcripts")

    op.drop_column("procedure_versions", "source_processed_at")
    op.drop_column("procedure_versions", "source_processing_error")
    op.drop_column("procedure_versions", "source_processing_status")
