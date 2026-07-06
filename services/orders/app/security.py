import hashlib
import hmac

from app.config import settings


def table_signature(cafe_id: str, table_number: int) -> str:
    """HMAC potpis koji QR kod stola nosi — gost ne može da falsifikuje sto."""
    message = f"{cafe_id}:{table_number}".encode()
    return hmac.new(settings.qr_secret.encode(), message, hashlib.sha256).hexdigest()


def verify_table_signature(cafe_id: str, table_number: int, sig: str) -> bool:
    return hmac.compare_digest(table_signature(cafe_id, table_number), sig)
