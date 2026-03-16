import uuid
from datetime import date, datetime

from pydantic import BaseModel


class AssignmentCreate(BaseModel):
    training_id: uuid.UUID
    user_ids: list[uuid.UUID] | None = None
    role_id: uuid.UUID | None = None
    location: str | None = None
    due_date: date | None = None
    assignment_type: str = "training"


class AssignmentOut(BaseModel):
    id: uuid.UUID
    training_id: uuid.UUID
    user_id: uuid.UUID
    assignment_type: str
    due_date: date | None
    status: str
    score: int | None
    attempts: int
    started_at: datetime | None
    completed_at: datetime | None
    training_title: str | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}
