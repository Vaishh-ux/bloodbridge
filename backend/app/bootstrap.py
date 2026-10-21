"""Create administrators from environment variables.

Public registration can never create admins. On hosts without a command line (Render's free plan)
set these in the dashboard instead of running create_admin.py:

    ADMIN_EMAIL  / ADMIN_PASSWORD   (optional ADMIN_NAME)
    ADMIN2_EMAIL / ADMIN2_PASSWORD  (optional ADMIN2_NAME)   - a second administrator

For each pair, at every start:
* If no user has that email, an ADMIN account is created.
* If an ADMIN with that email exists, its password is updated to the configured one.
* If the email belongs to a donor/patient/hospital account, nothing is changed.

Passwords are never logged.
"""
import logging
from typing import Dict

from app.auth import get_password_hash, verify_password
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, UserRole

logger = logging.getLogger("bloodbridge.bootstrap")


def ensure_admin(email: str, password: str, name: str = "Administrator", label: str = "ADMIN") -> str:
    email = (email or "").strip().lower()
    password = password or ""
    if not email and not password:
        return "skipped"
    if not email or "@" not in email:
        logger.warning("%s_EMAIL is missing or invalid; no admin account was created.", label)
        return "invalid"
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        logger.warning("%s_PASSWORD must be 8-72 characters; no admin account was created.", label)
        return "invalid"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            db.add(User(name=(name or "Administrator").strip()[:150], email=email, phone="+910000000000",
                        password_hash=get_password_hash(password), role=UserRole.ADMIN,
                        is_verified=True, is_active=True, is_blocked=False))
            db.commit()
            logger.info("Created administrator %s from %s_EMAIL.", email, label)
            return "created"
        if user.role != UserRole.ADMIN:
            logger.warning("%s_EMAIL %s belongs to a %s account; it was not changed.", label, email, user.role.value)
            return "conflict"
        if not verify_password(password, user.password_hash):
            user.password_hash = get_password_hash(password)
            user.is_blocked = False
            db.commit()
            logger.info("Updated the password of administrator %s from %s_PASSWORD.", email, label)
            return "updated"
        return "unchanged"
    except Exception:
        db.rollback()
        logger.exception("Could not create the administrator from %s_EMAIL.", label)
        return "error"
    finally:
        db.close()


def ensure_admin_from_env() -> Dict[str, str]:
    return {
        "ADMIN": ensure_admin(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD, settings.ADMIN_NAME, "ADMIN"),
        "ADMIN2": ensure_admin(settings.ADMIN2_EMAIL, settings.ADMIN2_PASSWORD, settings.ADMIN2_NAME, "ADMIN2"),
    }
