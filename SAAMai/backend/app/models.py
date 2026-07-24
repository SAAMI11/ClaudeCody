"""
models.py
=========
SQLAlchemy ORM models describing everything SAAMai stores locally:
users, chats, messages, attachments and per-user settings.

Storing chat history locally (instead of in the cloud) is what lets
SAAMai run fully offline and keeps user data private.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """A local user account. Accounts are entirely optional - a default
    'local' user is created automatically so SAAMai also works single-user
    with zero setup."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    language: Mapped[str] = mapped_column(String(8), default="de")
    theme: Mapped[str] = mapped_column(String(8), default="dark")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chats: Mapped[list["Chat"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    settings: Mapped[list["Setting"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Chat(Base):
    """A conversation, i.e. an ordered collection of messages."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), default="Neuer Chat")
    model: Mapped[str] = mapped_column(String(128), default="llama3.1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)

    owner: Mapped["User"] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    """A single chat message, either from the 'user' or the 'assistant'."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chat: Mapped["Chat"] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class Attachment(Base):
    """A file (document or image) attached to a message, plus any text
    that was extracted from it so it can be fed to the LLM as context.

    ``message_id`` is nullable because a file is uploaded (and text
    extracted) *before* the user hits send - it only gets linked to a
    message once that message is actually created. ``owner_id`` lets
    orphaned uploads still be cleaned up / attributed correctly."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(32))  # "pdf" | "docx" | "text" | "image"
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    message: Mapped["Message | None"] = relationship(back_populates="attachments")


class Setting(Base):
    """Generic per-user key/value settings store, used by the settings
    menu and by plugins that need to persist their own configuration."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(Text)

    owner: Mapped["User"] = relationship(back_populates="settings")
