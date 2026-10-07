"""Create the first AcxiomCRM administrator through an interactive local command.

Run after Alembic migrations:
    python -m app.bootstrap_admin --name "System Admin" --email admin@example.com
"""

import argparse
from getpass import getpass

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security import PasswordPolicyError, hash_password
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.models.user import User
from app.policies.authorization import RoleName


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the initial active Admin account.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--username")
    args = parser.parse_args()

    password = getpass("Admin password: ")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        password_hash = hash_password(password)
    except PasswordPolicyError as exc:
        raise SystemExit(str(exc)) from exc

    email = args.email.strip().lower()
    username = args.username.strip() if args.username else None
    with SessionLocal() as db:
        existing = db.scalar(
            select(User.id).where(
                (func.lower(User.email) == email) | (User.username == username if username else False)
            )
        )
        if existing:
            raise SystemExit("A user with those details already exists.")
        admin_role = db.scalar(select(Role).where(Role.name == RoleName.ADMIN.value))
        if admin_role is None:
            raise SystemExit("Admin role is missing. Run Alembic migrations first.")
        admin = User(
            name=args.name.strip(),
            email=email,
            username=username,
            password_hash=password_hash,
            role_id=admin_role.id,
            is_active=True,
        )
        db.add(admin)
        db.flush()
        db.add(
            AuditLog(
                user_id=admin.id,
                action="bootstrap_admin_created",
                entity_name="authentication",
                record_id=str(admin.id),
                result="success",
                details="Initial administrator created",
            )
        )
        db.commit()


if __name__ == "__main__":
    main()
