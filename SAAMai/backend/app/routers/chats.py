"""
routers/chats.py
=================
CRUD for conversations, full-text search across a user's chat history,
and chat export (Markdown/TXT/JSON).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_db
from ..models import Chat, Message, User
from ..schemas import ChatCreate, ChatDetailOut, ChatOut, ChatUpdate
from ..security import get_current_user
from ..services.export import export_chat

router = APIRouter(prefix="/api/chats", tags=["chats"])


def _get_owned_chat(db: Session, chat_id: int, user: User) -> Chat:
    chat = (
        db.query(Chat)
        .options(selectinload(Chat.messages))
        .filter(Chat.id == chat_id, Chat.owner_id == user.id)
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat nicht gefunden.")
    return chat


@router.get("", response_model=list[ChatOut])
def list_chats(
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lists chats, newest first. If ``q`` is given, searches both chat
    titles and message content (the in-chat search feature)."""
    query = db.query(Chat).filter(Chat.owner_id == user.id)
    if q:
        like = f"%{q}%"
        matching_chat_ids = (
            db.query(Message.chat_id).filter(Message.content.ilike(like)).distinct()
        )
        query = query.filter(or_(Chat.title.ilike(like), Chat.id.in_(matching_chat_ids)))
    return query.order_by(Chat.pinned.desc(), Chat.updated_at.desc()).all()


@router.post("", response_model=ChatOut, status_code=201)
def create_chat(payload: ChatCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chat = Chat(
        owner_id=user.id,
        title=payload.title or "Neuer Chat",
        model=payload.model or settings.default_text_model,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/{chat_id}", response_model=ChatDetailOut)
def get_chat(chat_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_owned_chat(db, chat_id, user)


@router.patch("/{chat_id}", response_model=ChatOut)
def update_chat(
    chat_id: int, payload: ChatUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    chat = _get_owned_chat(db, chat_id, user)
    if payload.title is not None:
        chat.title = payload.title
    if payload.pinned is not None:
        chat.pinned = payload.pinned
    if payload.model is not None:
        chat.model = payload.model
    db.commit()
    db.refresh(chat)
    return chat


@router.delete("/{chat_id}", status_code=204)
def delete_chat(chat_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chat = _get_owned_chat(db, chat_id, user)
    db.delete(chat)
    db.commit()
    return Response(status_code=204)


@router.get("/{chat_id}/export")
def export_chat_endpoint(
    chat_id: int,
    format: str = "md",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    chat = _get_owned_chat(db, chat_id, user)
    filename, mime, content = export_chat(chat, format)
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
