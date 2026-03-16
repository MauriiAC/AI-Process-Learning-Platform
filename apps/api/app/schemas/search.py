import uuid

from pydantic import BaseModel


class SearchResult(BaseModel):
    procedure_id: uuid.UUID
    procedure_version_id: uuid.UUID
    procedure_code: str
    procedure_title: str
    version_number: int
    training_id: uuid.UUID | None = None
    training_title: str | None = None
    snippet: str
    start_time: float | None = None
    end_time: float | None = None
    score: float
