import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import STATUS_FLOW, Order, OrderItem
from app.schemas import OrderCreate, OrderItemOut, OrderOut, StatusUpdate
from app.security import table_signature, verify_table_signature

logger = logging.getLogger("orders")
router = APIRouter()


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=str(order.id),
        cafe_id=order.cafe_id,
        table_number=order.table_number,
        status=order.status,
        note=order.note,
        total=order.total,
        created_at=order.created_at,
        items=[OrderItemOut(item_id=i.item_id, name=i.name,
                            unit_price=i.unit_price, qty=i.qty)
               for i in order.items],
    )


async def _notify_barkds(order: Order) -> None:
    """Šalje tiket Bar/KDS servisu. (U Fazi 4 postaje Kafka event.)"""
    payload = {
        "order_id": str(order.id),
        "cafe_id": order.cafe_id,
        "table_number": order.table_number,
        "status": order.status,
        "note": order.note,
        "created_at": order.created_at.isoformat(),
        "items": [{"name": i.name, "qty": i.qty} for i in order.items],
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.barkds_url}/internal/tickets", json=payload)
    except httpx.HTTPError:
        # porudžbina je sačuvana; bar će je povući pri sledećem osvežavanju
        logger.warning("Bar/KDS nedostupan — tiket %s nije odmah isporučen", order.id)


@router.post("/orders", response_model=OrderOut, status_code=201)
async def create_order(body: OrderCreate, session: AsyncSession = Depends(get_session)):
    if not verify_table_signature(body.cafe_id, body.table_number, body.sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")

    # validacija stavki kroz menu servis (cena se NIKAD ne prima od klijenta)
    ids = ",".join(i.item_id for i in body.items)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.menu_url}/internal/items",
                                    params={"ids": ids})
            resp.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Menu service unavailable")

    catalog = {item["id"]: item for item in resp.json()}
    order_items: list[OrderItem] = []
    total = 0
    for requested in body.items:
        item = catalog.get(requested.item_id)
        if item is None or item["cafe_id"] != body.cafe_id:
            raise HTTPException(status_code=400,
                                detail=f"Unknown item: {requested.item_id}")
        if not item["available"]:
            raise HTTPException(status_code=409,
                                detail=f"Item not available: {item['name']}")
        total += item["price"] * requested.qty
        order_items.append(OrderItem(item_id=requested.item_id, name=item["name"],
                                     unit_price=item["price"], qty=requested.qty))

    order = Order(cafe_id=body.cafe_id, table_number=body.table_number,
                  note=body.note, total=total, items=order_items)
    session.add(order)
    await session.commit()

    await _notify_barkds(order)
    return _order_out(order)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_out(order)


@router.get("/tables/{cafe_id}/{table_number}/orders", response_model=list[OrderOut])
async def table_orders(cafe_id: str, table_number: int, sig: str,
                       session: AsyncSession = Depends(get_session)):
    """Aktivne porudžbine stola — gost vidi samo svoj sto (potpis iz QR-a)."""
    if not verify_table_signature(cafe_id, table_number, sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")
    result = await session.execute(
        select(Order)
        .where(Order.cafe_id == cafe_id, Order.table_number == table_number,
               Order.status.notin_(["DELIVERED", "CANCELLED"]))
        .order_by(Order.created_at.desc())
    )
    return [_order_out(o) for o in result.scalars().all()]


@router.patch("/internal/orders/{order_id}/status", response_model=OrderOut)
async def update_status(order_id: uuid.UUID, body: StatusUpdate,
                        session: AsyncSession = Depends(get_session)):
    """Interna ruta — Bar/KDS javlja promenu statusa."""
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if body.status not in STATUS_FLOW.get(order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition {order.status} -> {body.status}",
        )
    order.status = body.status
    await session.commit()
    return _order_out(order)


if settings.app_env == "dev":
    @router.get("/dev/sign")
    def dev_sign(cafe_id: str, table_number: int):
        """Pomoćna dev ruta: generiše QR potpis stola (nedostupna kroz gateway)."""
        return {"cafe_id": cafe_id, "table_number": table_number,
                "sig": table_signature(cafe_id, table_number)}
