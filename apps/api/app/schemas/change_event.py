import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ChangeEventCreate(BaseModel):
    title: str
    description: str
    source_type: str = "manual"
    status: str = "draft"
    effective_from: date | None = None
    context_json: dict | None = None


class ChangeEventOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    source_type: str
    status: str
    effective_from: date | None
    context_json: dict | None
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ProcedureImpactAssessmentOut(BaseModel):
    id: uuid.UUID
    change_event_id: uuid.UUID
    procedure_id: uuid.UUID
    procedure_title: str
    procedure_version_id: uuid.UUID | None
    version_number: int | None = None
    training_id: uuid.UUID | None = None
    training_title: str | None = None
    confidence: float
    impact_level: str
    rationale: str | None
    recommendation: str | None
    status: str
    created_at: datetime
