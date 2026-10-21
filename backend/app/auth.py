"""Password hashing, JWT creation/validation and role-based access dependencies."""
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

_bearer = HTTPBearer(auto_error=False)


# --- Passwords --------------------------------------------------------------------
# bcrypt is used directly: passlib 1.7.4 is unmaintained and breaks with bcrypt>=4.1.
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# --- Tokens -----------------------------------------------------------------------
def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def user_from_token(db: Session, token: str) -> Optional[User]:
    user_id = decode_token(token)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active or user.is_blocked:
        return None
    return user


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in to continue.")
    user = user_from_token(db, creds.credentials)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please log in again.")
    return user


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if creds is None:
        return None
    return user_from_token(db, creds.credentials)


def require_roles(roles: Iterable[UserRole]):
    allowed = set(roles)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to perform this action.")
        return current_user

    return _checker


# --- Basic in-memory rate limiting for auth endpoints ---------------------------
_attempts: dict = defaultdict(deque)


def auth_rate_limit(request: Request) -> None:
    if settings.ENVIRONMENT == "test":
        return
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _attempts[ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.AUTH_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Please wait a minute and try again.")
    window.append(now)
