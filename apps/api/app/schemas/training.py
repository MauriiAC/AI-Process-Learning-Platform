import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.generated_content import GeneratedTrainingStructure


class TrainingCreate(BaseModel):
    procedure_version_id: uuid.UUID
    title: str | None = None
    summary: str | None = None


class TrainingStructureOut(BaseModel):
    structure_json: GeneratedTrainingStructure

    model_config = {"from_attributes": True}


class TrainingOut(BaseModel):
    id: uuid.UUID
    procedure_version_id: uuid.UUID
    title: str
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    summary: str | None = None
    procedure_id: uuid.UUID | None = None
    procedure_code: str | None = None
    procedure_title: str | None = None
    version_number: int | None = None
    source_asset_type: str | None = None
    source_storage_key: str | None = None
    source_mime: str | None = None
    source_size: int | None = None
    structure: TrainingStructureOut | None = None

    model_config = {"from_attributes": True}


class TrainingIterateRequest(BaseModel):
    instruction: str


class GenerateResponse(BaseModel):
    job_id: uuid.UUID
    training_id: uuid.UUID | None = None
