"""
routers/documents.py
=====================
File upload endpoint used for both "read documents" (PDF/Word/text) and
"analyse images" features. Files are stored under data/uploads and text
is extracted immediately so it's ready to attach to the next chat
message.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import UPLOAD_DIR, settings
from ..database import get_db
from ..models import Attachment, User
from ..schemas import AttachmentOut
from ..security import get_current_user
from ..services.documents import UnsupportedFileTypeError, detect_file_type, extract_text

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=AttachmentOut, status_code=201)
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Datei ist groesser als {settings.max_upload_mb} MB.")

    try:
        file_type = detect_file_type(file.filename or "upload")
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored_name = f"{uuid.uuid4().hex}_{Path(file.filename or 'upload').name}"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(raw)

    extracted = extract_text(stored_path, file_type) if file_type != "image" else None

    attachment = Attachment(
        owner_id=user.id,
        filename=file.filename or stored_name,
        file_path=str(stored_path),
        file_type=file_type,
        extracted_text=extracted,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment
