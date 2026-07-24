"""
schemas.py
==========
Pydantic request/response models (the API's public "shape"). Keeping
these separate from the SQLAlchemy models in models.py means the
database layout can evolve without automatically changing the API
contract, and vice versa.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Auth -------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    language: str
    theme: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Chats --------------------------------------------------------------

class ChatCreate(BaseModel):
    title: str | None = None
    model: str | None = None


class ChatUpdate(BaseModel):
    title: str | None = None
    pinned: bool | None = None
    model: str | None = None


class ChatOut(BaseModel):
    id: int
    title: str
    model: str
    pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Messages -------------------------------------------------------------

class AttachmentOut(BaseModel):
    id: int
    filename: str
    file_type: str

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str
    attachment_ids: list[int] = Field(default_factory=list)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    attachments: list[AttachmentOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ChatDetailOut(ChatOut):
    messages: list[MessageOut] = Field(default_factory=list)


# --- Settings ---------------------------------------------------------

class SettingIn(BaseModel):
    key: str
    value: str


class SettingOut(BaseModel):
    key: str
    value: str

    model_config = ConfigDict(from_attributes=True)


# --- Models (Ollama) ----------------------------------------------------

class ModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class ModelPullRequest(BaseModel):
    name: str
