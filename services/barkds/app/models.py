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
    """Zahtev gosta bez porudžbine: poziv konobara ili traženje računa."""
    cafe_id: str
    table_number: int
    kind: str  # "waiter" | "bill"
    status: str = "OPEN"  # OPEN | RESOLVED
    created_at: datetime

    class Settings:
        name = "requests"
        indexes = ["cafe_id"]
