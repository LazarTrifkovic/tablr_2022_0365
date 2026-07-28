from datetime import datetime

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    item_id: str
    qty: int = Field(gt=0, le=50)


class OrderCreate(BaseModel):
    cafe_id: str
    table_number: int = Field(ge=1, le=500)
    sig: str
    note: str | None = Field(default=None, max_length=300)
    items: list[OrderItemIn] = Field(min_length=1, max_length=50)


class OrderItemOut(BaseModel):
    id: int
    item_id: str
    name: str
    unit_price: int
    qty: int
    paid: bool = False


class BillItemOut(BaseModel):
    """Jedna stavka na zbirnom računu stola (jedna po OrderItem-u, selektabilna)."""
    order_item_id: int
    name: str
    unit_price: int
    qty: int
    line_total: int
    paid: bool


class BillOut(BaseModel):
    cafe_id: str
    table_number: int
    items: list[BillItemOut]
    subtotal: int      # zbir svih stavki
    paid_total: int    # zbir već plaćenih
    remaining: int     # preostalo za naplatu


class SettleIn(BaseModel):
    """Konobar naplaćuje izabrane stavke (keš/kartica na licu mesta)."""
    order_item_ids: list[int] = Field(min_length=1)
    payment_method: str | None = None


class OrderOut(BaseModel):
    id: str
    cafe_id: str
    table_number: int
    status: str
    note: str | None
    total: int
    taken_by: str | None = None
    payment_method: str | None = None
    rating: int | None = None
    rating_comment: str | None = None
    created_at: datetime
    accepted_at: datetime | None = None
    ready_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None
    items: list[OrderItemOut]


class StatusUpdate(BaseModel):
    status: str
    taken_by: str | None = None
    # konobar pri isporuci označi kako je gost platio: "cash" | "card"
    payment_method: str | None = None


class RatingIn(BaseModel):
    """Ocena gosta posle isporuke — potpis iz QR-a dokazuje sto."""
    sig: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=300)
