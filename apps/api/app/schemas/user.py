import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    location: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRoleRef(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class UserRoleAssignmentInput(BaseModel):
    id: uuid.UUID | None = None
    role_id: uuid.UUID
    location: str | None = None
    status: str = "active"
    starts_on: date | None = None
    ends_on: date | None = None


class UserRoleAssignmentOut(BaseModel):
    id: uuid.UUID
    role_id: uuid.UUID
    location: str | None
    status: str
    starts_on: date | None
    ends_on: date | None
    created_at: datetime
    role: UserRoleRef

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    location: str | None = None
    role_assignments: list[UserRoleAssignmentInput] = Field(default_factory=list)


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    location: str | None = None
    role_assignments: list[UserRoleAssignmentInput] | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    location: str | None
    created_at: datetime
    role_assignments: list[UserRoleAssignmentOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
