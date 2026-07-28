from datetime import datetime

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel


class TicketItem(BaseModel):
    name: str
    qty: int


class Ticket(Document):
    order_id: str
    cafe_id: str
    table_number: int
    status: str = "CREATED"
    note: str | None = None
    items: list[TicketItem]
    created_at: datetime

    class Settings:
        name = "tickets"
        indexes = [IndexModel("order_id", unique=True), "cafe_id"]


class ServiceRequest(Document):
    """Zahtev gosta bez porudžbine: poziv konobara, traženje računa ili
    naplata izabranih stavki (podela računa uživo kod konobara)."""
    cafe_id: str
    table_number: int
    kind: str  # "waiter" | "bill" | "bill_split"
    status: str = "OPEN"  # OPEN | RESOLVED
    created_at: datetime
    detail: str | None = None          # čitljiv sažetak izabranih stavki
    item_ids: list[int] | None = None  # OrderItem id-jevi za naplatu (bill_split)
    amount: int | None = None          # iznos izabranih stavki

    class Settings:
        name = "requests"
        indexes = ["cafe_id"]
