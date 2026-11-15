
from getpass import getpass

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password


def create_admin():
    db = SessionLocal()

    try:
        print("\n=== AI Creative Studio - Initial Administrator ===\n")

        name = input("Administrator name: ").strip()
        email = input("Administrator email: ").strip().lower()
        password = getpass("Administrator password: ")
        confirm_password = getpass("Confirm administrator password: ")

        if not name or not email:
            print("Name and email are required.")
            return

        if len(password) < 12:
            print("Password must contain at least 12 characters.")
            return

        if password != confirm_password:
            print("Passwords do not match.")
            return

        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            print("An account with this email already exists.")
            return

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="systemadministrator",
            can_access_image=True,
            can_access_audio=True,
            can_access_video=True,
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print("\nAdministrator account created successfully.")
        print(f"Email: {email}")
        print("Role: systemadministrator")

    except Exception as error:
        db.rollback()
        print(f"\nAdministrator creation failed: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
