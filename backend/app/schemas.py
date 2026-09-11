import uuid

from pydantic import BaseModel, EmailStr, Field


class MagicLinkRequest(BaseModel):
    email: EmailStr


class Message(BaseModel):
    message: str


class MemberRead(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str


class HouseholdRead(BaseModel):
    id: uuid.UUID
    name: str
    members: list[MemberRead] = Field(default_factory=list)


class MeRead(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    household: HouseholdRead


class HealthRead(BaseModel):
    status: str
