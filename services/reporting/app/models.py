from beanie import Document
from pymongo import IndexModel


class CafeStats(Document):
    """READ MODEL (CQRS): pre-sračunata analitika smene po kafiću. Projektor je
    inkrementalno održava iz događaja — upit je čisto čitanje, bez računanja."""
    cafe_id: str
    orders_count: int = 0        # broj isporučenih porudžbina
    revenue: int = 0             # ukupan pazar (RSD)
    prep_seconds_sum: int = 0    # za prosečno vreme pripreme
    prep_seconds_count: int = 0
    rating_sum: int = 0          # za prosečnu ocenu
    rating_count: int = 0
    cash_count: int = 0
    card_count: int = 0

    class Settings:
        name = "cafe_stats"
        indexes = [IndexModel("cafe_id", unique=True)]


class ProcessedEvent(Document):
    """Dedup: Kafka je 'at-least-once', pa isti događaj može stići dvaput. `key` je
    '{order_id}:{tip}' — ako već postoji, agregat se NE ažurira ponovo (idempotentno)."""
    key: str

    class Settings:
        name = "processed_events"
        indexes = [IndexModel("key", unique=True)]
