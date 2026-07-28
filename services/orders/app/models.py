import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# dozvoljene tranzicije statusa porudžbine
STATUS_FLOW: dict[str, set[str]] = {
    "CREATED": {"ACCEPTED", "CANCELLED"},
    "ACCEPTED": {"READY", "CANCELLED"},
    "READY": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          default=uuid.uuid4)
    cafe_id: Mapped[str] = mapped_column(String(32), index=True)
    table_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="CREATED")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    total: Mapped[int] = mapped_column(Integer)
    # ko od osoblja je preuzeo porudžbinu (izbor konobara u smeni — Faza 3 UI)
    taken_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # način plaćanja koji konobar označi pri isporuci: "cash" | "card"
    # (evidencija za smenu; pravi Payments/Stripe tok stiže kasnije)
    payment_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # ocena gosta 1–5 + opcioni komentar (unosi se sa gost aplikacije posle isporuke)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # vremena tranzicija — osnova za statistiku brzine pripreme (po piću/konobaru)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    item_id: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    unit_price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)
    # da li je ova stavka već plaćena (podela računa — plaća se po stavci)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped[Order] = relationship(back_populates="items")
