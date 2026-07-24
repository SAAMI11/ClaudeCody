"""
security.py
============
Local authentication: password hashing (bcrypt via passlib) and JWT
session tokens (python-jose). Everything runs on-device - there is no
external identity provider, so accounts work fully offline.

User accounts are optional (see routers/auth.py: a default "local" user
is auto-provisioned), but when enabled, passwords are never stored in
plain text and tokens are signed with a locally generated secret.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None


def get_or_create_default_user(db: Session) -> User:
    """SAAMai works without ever creating an account: a 'local' user is
    provisioned automatically on first run so the chat UI is usable
    immediately."""
    user = db.query(User).filter(User.username == "local").first()
    if user is None:
        user = User(username="local", password_hash=hash_password("local"), language=settings.default_language)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Resolves the current user from a bearer token. Falls back to the
    default local user when no token is supplied, keeping the API usable
    without a login step for single-user, offline setups."""
    if not token:
        return get_or_create_default_user(db)

    username = _decode_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
