"""Create an administrator from environment variables (ADMIN_EMAIL / ADMIN_PASSWORD).

Public registration can never create admins. On hosts without a command line (Render free plan)
set these two variables in the dashboard instead of running create_admin.py:

* If no user has that email, an ADMIN account is created.
* If an ADMIN with that email exists, its password is updated to ADMIN_PASSWORD.
* If the email belongs to a donor/patient/hospital account, nothing is changed.

The password is never logged.
"""
import logging

from app.auth import get_password_hash, verify_password
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, UserRole

logger = logging.getLogger("bloodbridge.bootstrap")


def ensure_admin_from_env() -> str:
    email = (settings.ADMIN_EMAIL or "").strip().lower()
    password = settings.ADMIN_PASSWORD or ""
    if not email and not password:
        return "skipped"
    if not email or "@" not in email:
        logger.warning("ADMIN_EMAIL is missing or invalid; no admin account was created.")
        return "invalid"
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        logger.warning("ADMIN_PASSWORD must be 8-72 characters; no admin account was created.")
        return "invalid"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            db.add(User(name=(settings.ADMIN_NAME or "Administrator").strip()[:150], email=email,
                        phone="+910000000000", password_hash=get_password_hash(password),
                        role=UserRole.ADMIN, is_verified=True, is_active=True, is_blocked=False))
            db.commit()
            logger.info("Created administrator %s from ADMIN_EMAIL.", email)
            return "created"
        if user.role != UserRole.ADMIN:
            logger.warning("ADMIN_EMAIL %s belongs to a %s account; it was not changed.", email, user.role.value)
            return "conflict"
        if not verify_password(password, user.password_hash):
            user.password_hash = get_password_hash(password)
            user.is_blocked = False
            db.commit()
            logger.info("Updated the password of administrator %s from ADMIN_PASSWORD.", email)
            return "updated"
        return "unchanged"
    except Exception:
        db.rollback()
        logger.exception("Could not create the administrator from ADMIN_EMAIL.")
        return "error"
    finally:
        db.close()
