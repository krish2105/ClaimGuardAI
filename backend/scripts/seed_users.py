"""Create the schema (if needed) and two demo login accounts.

This is a portfolio demo on entirely synthetic data, so the demo
credentials are deliberately public (shown on the login page itself) —
there is no real PII or liability at stake. Real deployments would replace
this with real account provisioning.

Idempotent: skips a username that already exists rather than resetting its
password, so re-running this after someone changes a demo password locally
doesn't silently revert it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.auth import hash_password  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402

DEMO_USERS = [
    {"username": "adjuster", "password": "adjuster123", "role": "adjuster"},
    {"username": "admin", "password": "admin123", "role": "admin"},
]


def main() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        created = []
        for demo in DEMO_USERS:
            if db.query(User).filter(User.username == demo["username"]).first() is not None:
                continue
            db.add(User(
                username=demo["username"],
                password_hash=hash_password(demo["password"]),
                role=demo["role"],
            ))
            created.append(demo["username"])
        db.commit()
        print(f"Created {len(created)} demo user(s): {created or 'none (already existed)'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
