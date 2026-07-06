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
    item_id: str
    name: str
    unit_price: int
    qty: int


class OrderOut(BaseModel):
    id: str
    cafe_id: str
    table_number: int
    status: str
    note: str | None
    total: int
    taken_by: str | None = None
    created_at: datetime
    accepted_at: datetime | None = None
    ready_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None
    items: list[OrderItemOut]


class StatusUpdate(BaseModel):
    status: str
    taken_by: str | None = None
