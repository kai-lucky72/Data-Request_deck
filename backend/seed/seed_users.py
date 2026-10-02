import json
from pathlib import Path

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password


def seed_users():
    db = SessionLocal()
    try:
        seed_file = Path(__file__).parent / "users.json"
        with open(seed_file, "r", encoding="utf-8") as f:
            users_data = json.load(f)

        created = 0
        skipped = 0

        for data in users_data:
            existing = db.query(User).filter(User.email == data["email"]).first()
            if existing:
                print(f"Skipped (already exists): {data['email']}")
                skipped += 1
                continue

            user = User(
                email=data["email"],
                password_hash=hash_password(data["password"]),
                role=UserRole(data["role"]),
                name=data["name"],
                organisation=data.get("organisation"),
                is_active=True,
            )
            db.add(user)
            created += 1
            print(f"Created: {data['email']} ({data['role']})")

        db.commit()
        print(f"\nDone. Created: {created}, Skipped: {skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()