import hashlib
import hmac

from app.config import settings


def table_signature(cafe_id: str, table_number: int) -> str:
    """Isti HMAC kao u orders/barkds — QR kod stola nosi ovaj potpis."""
    message = f"{cafe_id}:{table_number}".encode()
    return hmac.new(settings.qr_secret.encode(), message, hashlib.sha256).hexdigest()
