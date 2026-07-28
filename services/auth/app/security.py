from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_token(*, user_id: str, email: str, role: str, cafe_id: str, name: str) -> str:
    """JWT koji nosi identitet i ulogu osoblja; gateway ga validira i prosleđuje kontekst."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "cafe_id": cafe_id,
        "name": name,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
