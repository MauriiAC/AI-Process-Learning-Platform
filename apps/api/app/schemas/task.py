import uuid

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None


class TaskUpdate(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None


class TaskRoleRef(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class TaskProcedureRef(BaseModel):
    id: uuid.UUID
    procedure_id: uuid.UUID
    code: str
    title: str
    is_primary: bool = False


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    location: str | None
    roles: list[TaskRoleRef] = []
    procedures: list[TaskProcedureRef] = []

    model_config = {"from_attributes": True}


class TrainingSuggestion(BaseModel):
    procedure_id: uuid.UUID | None = None
    procedure_version_id: uuid.UUID | None = None
    training_id: uuid.UUID | None = None
    title: str
    score: float
    snippet: str | None = None
