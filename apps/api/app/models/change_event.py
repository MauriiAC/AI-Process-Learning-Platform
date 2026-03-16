import uuid
from datetime import date, datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), default="manual")
    status: Mapped[str] = mapped_column(String(50), default="draft")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    context_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    embedding = mapped_column(Vector(3072), nullable=True)

    impact_assessments = relationship("ProcedureImpactAssessment", back_populates="change_event", lazy="selectin")


class ProcedureImpactAssessment(Base):
    __tablename__ = "procedure_impact_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("change_events.id", ondelete="CASCADE")
    )
    procedure_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("procedures.id", ondelete="CASCADE"))
    procedure_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("procedure_versions.id"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    impact_level: Mapped[str] = mapped_column(String(50), default="medium")
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    change_event = relationship("ChangeEvent", back_populates="impact_assessments", lazy="selectin")
    procedure = relationship("Procedure", lazy="selectin")
    procedure_version = relationship("ProcedureVersion", lazy="selectin")
