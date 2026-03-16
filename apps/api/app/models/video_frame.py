import uuid

from sqlalchemy import String, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VideoFrame(Base):
    __tablename__ = "video_frames"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    procedure_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("procedure_versions.id", ondelete="CASCADE"),
    )
    timestamp: Mapped[float] = mapped_column(Float)
    storage_key: Mapped[str] = mapped_column(String(1000))
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    procedure_version = relationship("ProcedureVersion", back_populates="frames", lazy="selectin")
