"""Procedure-centric domain expansion

Revision ID: 002_procedure_centric_domain
Revises: 001_initial
Create Date: 2026-03-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "002_procedure_centric_domain"
down_revision: Union[str, None] = "002_ai_usage_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trainings", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("assignments", sa.Column("assignment_type", sa.String(length=50), nullable=False, server_default="training"))

    op.create_table(
        "roles",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    op.create_table(
        "user_role_assignments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("role_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE")),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "role_task_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE")),
        sa.Column("task_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE")),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "procedures",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_role_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id")),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_procedures_code", "procedures", ["code"], unique=True)

    op.create_table(
        "procedure_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("procedure_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="CASCADE")),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("content_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("embedding", Vector(3072), nullable=True),
    )

    op.create_table(
        "task_procedure_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE")),
        sa.Column("procedure_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="CASCADE")),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "training_procedure_version_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("training_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("trainings.id", ondelete="CASCADE")),
        sa.Column("procedure_version_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedure_versions.id", ondelete="CASCADE")),
        sa.Column("relation_type", sa.String(50), nullable=False, server_default="primary"),
        sa.Column("coverage_score", sa.Float(), nullable=True),
    )

    op.create_table(
        "user_procedure_compliance",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("procedure_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="CASCADE")),
        sa.Column("procedure_version_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedure_versions.id")),
        sa.Column("role_assignment_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("user_role_assignments.id")),
        sa.Column("training_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("trainings.id")),
        sa.Column("assignment_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("assignments.id")),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_score", sa.Integer(), nullable=True),
        sa.Column("evidence_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "incident_procedure_hypotheses",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE")),
        sa.Column("procedure_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id")),
        sa.Column("procedure_version_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedure_versions.id")),
        sa.Column("task_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id")),
        sa.Column("training_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("trainings.id")),
        sa.Column("source", sa.String(50), nullable=False, server_default="ai"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="suggested"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "change_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("context_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("embedding", Vector(3072), nullable=True),
    )

    op.create_table(
        "procedure_impact_assessments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("change_event_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("change_events.id", ondelete="CASCADE")),
        sa.Column("procedure_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="CASCADE")),
        sa.Column("procedure_version_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("procedure_versions.id")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("impact_level", sa.String(50), nullable=False, server_default="medium"),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("procedure_impact_assessments")
    op.drop_table("change_events")
    op.drop_table("incident_procedure_hypotheses")
    op.drop_table("user_procedure_compliance")
    op.drop_table("training_procedure_version_links")
    op.drop_table("task_procedure_links")
    op.drop_table("procedure_versions")
    op.drop_index("ix_procedures_code", table_name="procedures")
    op.drop_table("procedures")
    op.drop_table("role_task_links")
    op.drop_table("user_role_assignments")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")
    op.drop_column("assignments", "assignment_type")
    op.drop_column("trainings", "summary")
