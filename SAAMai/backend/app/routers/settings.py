"""
routers/settings.py
====================
Per-user key/value settings store backing the settings menu (theme,
language, default model, and anything a plugin wants to persist).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Setting, User
from ..schemas import SettingIn, SettingOut
from ..security import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Setting).filter(Setting.owner_id == user.id).all()


@router.put("", response_model=SettingOut)
def upsert_setting(payload: SettingIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    setting = (
        db.query(Setting).filter(Setting.owner_id == user.id, Setting.key == payload.key).first()
    )
    if setting is None:
        setting = Setting(owner_id=user.id, key=payload.key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value

    # Keep the well-known theme/language settings in sync on the user
    # record too, since several endpoints read them from there directly.
    if payload.key == "theme":
        user.theme = payload.value
    elif payload.key == "language":
        user.language = payload.value

    db.commit()
    db.refresh(setting)
    return setting
