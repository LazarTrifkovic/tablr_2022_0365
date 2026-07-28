import hashlib
import hmac

from app.config import settings


def verify_table_signature(cafe_id: str, table_number: int, sig: str) -> bool:
    """Isti HMAC kao u orders — dokazuje da onaj ko plaća zaista sedi za tim stolom."""
    message = f"{cafe_id}:{table_number}".encode()
    expected = hmac.new(settings.qr_secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
