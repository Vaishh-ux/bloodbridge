"""Create (or promote) an administrator account.

    python create_admin.py --email admin@yourorg.org --name "Site Admin"

You are prompted for the password; it is never echoed or logged.
Admins cannot be created through public registration.
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.auth import get_password_hash  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="Administrator")
    p.add_argument("--phone", default="+910000000000")
    args = p.parse_args()

    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password (min 8 chars): ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")

    init_db()
    db = SessionLocal()
    try:
        email = args.email.strip().lower()
        user = db.query(User).filter(User.email == email).first()
        if user:
            if user.role != UserRole.ADMIN:
                sys.exit(f"{email} already exists with role {user.role.value}; refusing to change it.")
            user.password_hash = get_password_hash(password)
            print(f"Updated password for existing admin {email}.")
        else:
            db.add(User(name=args.name, email=email, phone=args.phone, password_hash=get_password_hash(password),
                        role=UserRole.ADMIN, is_verified=True, is_active=True))
            print(f"Created admin {email}.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
