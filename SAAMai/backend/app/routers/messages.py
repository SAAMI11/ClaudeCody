"""
routers/messages.py
====================
Sends a message to the local model and streams the reply back as it is
generated (chunked HTTP response), which is what makes the UI feel fast
even on modest hardware - tokens appear as soon as Ollama produces them
instead of waiting for the full answer.

Note on database sessions: FastAPI closes a ``Depends(get_db)`` session
as soon as the endpoint function *returns*, which happens immediately
for a StreamingResponse (before the generator body has actually run).
So the streaming generator below opens its own short-lived session to
persist the assistant's reply once streaming is complete.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from ..database import SessionLocal, get_db
from ..models import Attachment, Chat, Message, User
from ..schemas import MessageCreate
from ..security import get_current_user
from ..services import llm
from ..services.documents import extract_text
from ..services.plugin_loader import PluginContext, registry

router = APIRouter(prefix="/api/chats/{chat_id}/messages", tags=["messages"])


def _build_history_for_model(chat: Chat) -> list[dict]:
    """Turns stored messages into the {role, content} list Ollama
    expects, folding any extracted document text into the relevant
    message so the model can actually see it."""
    history = []
    for msg in chat.messages:
        content = msg.content
        doc_snippets = [
            f"\n\n[Anhang: {a.filename}]\n{a.extracted_text}"
            for a in msg.attachments
            if a.file_type != "image" and a.extracted_text
        ]
        history.append({"role": msg.role, "content": content + "".join(doc_snippets)})
    return history


@router.post("/stream")
def send_message_stream(
    chat_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .options(selectinload(Chat.messages).selectinload(Message.attachments))
        .filter(Chat.id == chat_id, Chat.owner_id == user.id)
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat nicht gefunden.")

    if not payload.content.strip() and not payload.attachment_ids:
        raise HTTPException(status_code=400, detail="Nachricht darf nicht leer sein.")

    context = PluginContext(chat_id=chat.id, user_id=user.id)
    prompt_text = registry.run_before_prompt(payload.content, context)

    user_message = Message(chat_id=chat.id, role="user", content=prompt_text)
    db.add(user_message)
    db.flush()  # assign user_message.id without committing yet

    attachments: list[Attachment] = []
    if payload.attachment_ids:
        attachments = (
            db.query(Attachment)
            .filter(
                Attachment.id.in_(payload.attachment_ids),
                Attachment.owner_id == user.id,
                Attachment.message_id.is_(None),
            )
            .all()
        )
        for att in attachments:
            att.message_id = user_message.id

    if chat.title == "Neuer Chat" and prompt_text.strip():
        chat.title = prompt_text.strip()[:60]

    db.commit()
    db.refresh(chat)

    history = _build_history_for_model(chat)

    def _read_b64(path: str) -> str:
        with open(path, "rb") as f:
            return llm.encode_image(f.read())

    images_b64 = [_read_b64(a.file_path) for a in attachments if a.file_type == "image"]

    model = chat.model
    if images_b64:
        # A dedicated vision model understands images far better than a
        # text-only one; use it automatically when an image is attached.
        from ..config import settings as app_settings

        model = app_settings.default_vision_model

    async def generate():
        collected = ""
        error_message: str | None = None
        try:
            async for token in llm.chat_stream(model, history, images_b64 or None):
                collected += token
                yield token
        except llm.LLMError as exc:
            error_message = str(exc)
            yield f"\n\n[Fehler: {error_message}]"

        final_text = registry.run_after_response(collected, context) if collected else error_message or ""
        session = SessionLocal()
        try:
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=final_text or "(keine Antwort erhalten)",
            )
            session.add(assistant_message)
            session.commit()
        finally:
            session.close()

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
