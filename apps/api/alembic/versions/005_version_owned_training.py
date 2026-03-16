"""Move source asset ownership to procedure versions

Revision ID: 005_version_owned_training
Revises: 004_drop_user_role
Create Date: 2026-03-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_version_owned_training"
down_revision: Union[str, None] = "005_role_refs_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("procedure_versions", sa.Column("source_asset_type", sa.String(length=50), nullable=True))
    op.add_column("procedure_versions", sa.Column("source_storage_key", sa.String(length=1000), nullable=True))
    op.add_column("procedure_versions", sa.Column("source_mime", sa.String(length=100), nullable=True))
    op.add_column("procedure_versions", sa.Column("source_size", sa.BigInteger(), nullable=True))

    op.add_column(
        "trainings",
        sa.Column("procedure_version_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_trainings_procedure_version_id",
        "trainings",
        "procedure_versions",
        ["procedure_version_id"],
        ["id"],
        ondelete="CASCADE",
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE trainings AS t
            SET procedure_version_id = link.procedure_version_id
            FROM (
                SELECT DISTINCT ON (training_id) training_id, procedure_version_id
                FROM training_procedure_version_links
                ORDER BY training_id, id
            ) AS link
            WHERE t.id = link.training_id
            """
        )
    )

    missing_links = conn.execute(
        sa.text("SELECT COUNT(*) FROM trainings WHERE procedure_version_id IS NULL")
    ).scalar_one()
    if missing_links:
        raise RuntimeError(
            "Cannot migrate to 1:1 training ownership because some trainings are not linked to any procedure version."
        )

    op.alter_column("trainings", "procedure_version_id", nullable=False)
    op.create_unique_constraint(
        "uq_trainings_procedure_version_id",
        "trainings",
        ["procedure_version_id"],
    )
    op.create_unique_constraint(
        "uq_procedure_versions_procedure_id_version_number",
        "procedure_versions",
        ["procedure_id", "version_number"],
    )

    op.drop_constraint(
        "user_procedure_compliance_training_id_fkey",
        "user_procedure_compliance",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "user_procedure_compliance_training_id_fkey",
        "user_procedure_compliance",
        "trainings",
        ["training_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "incident_procedure_hypotheses_training_id_fkey",
        "incident_procedure_hypotheses",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "incident_procedure_hypotheses_training_id_fkey",
        "incident_procedure_hypotheses",
        "trainings",
        ["training_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_table("training_procedure_version_links")
    op.drop_table("training_assets")


def downgrade() -> None:
    op.create_table(
        "training_assets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("training_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("trainings.id", ondelete="CASCADE")),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
    )

    op.create_table(
        "training_procedure_version_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("training_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("trainings.id", ondelete="CASCADE")),
        sa.Column(
            "procedure_version_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procedure_versions.id", ondelete="CASCADE"),
        ),
        sa.Column("relation_type", sa.String(length=50), nullable=False, server_default="primary"),
        sa.Column("coverage_score", sa.Float(), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO training_procedure_version_links (id, training_id, procedure_version_id, relation_type, coverage_score)
            SELECT gen_random_uuid(), id, procedure_version_id, 'primary', NULL
            FROM trainings
            WHERE procedure_version_id IS NOT NULL
            """
        )
    )

    op.drop_constraint(
        "incident_procedure_hypotheses_training_id_fkey",
        "incident_procedure_hypotheses",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "incident_procedure_hypotheses_training_id_fkey",
        "incident_procedure_hypotheses",
        "trainings",
        ["training_id"],
        ["id"],
    )
    op.drop_constraint(
        "user_procedure_compliance_training_id_fkey",
        "user_procedure_compliance",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "user_procedure_compliance_training_id_fkey",
        "user_procedure_compliance",
        "trainings",
        ["training_id"],
        ["id"],
    )

    op.drop_constraint("uq_procedure_versions_procedure_id_version_number", "procedure_versions", type_="unique")
    op.drop_constraint("uq_trainings_procedure_version_id", "trainings", type_="unique")
    op.drop_constraint("fk_trainings_procedure_version_id", "trainings", type_="foreignkey")
    op.drop_column("trainings", "procedure_version_id")

    op.drop_column("procedure_versions", "source_size")
    op.drop_column("procedure_versions", "source_mime")
    op.drop_column("procedure_versions", "source_storage_key")
    op.drop_column("procedure_versions", "source_asset_type")
