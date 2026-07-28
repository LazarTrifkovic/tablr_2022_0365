import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.events import publish_order_event
from app.models import STATUS_FLOW, Order, OrderItem
from app.schemas import (BillItemOut, BillOut, CancelIn, OrderCreate, OrderItemOut,
                         OrderOut, RatingIn, SettleIn, StatusUpdate)
from app.security import table_signature, verify_table_signature

# koliko dugo posle isporuke gost i dalje vidi porudžbinu (da može da oceni)
DELIVERED_VISIBLE = timedelta(hours=3)

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
        taken_by=order.taken_by,
        payment_method=order.payment_method,
        rating=order.rating,
        rating_comment=order.rating_comment,
        created_at=order.created_at,
        accepted_at=order.accepted_at,
        ready_at=order.ready_at,
        delivered_at=order.delivered_at,
        cancelled_at=order.cancelled_at,
        items=[OrderItemOut(id=i.id, item_id=i.item_id, name=i.name,
                            unit_price=i.unit_price, qty=i.qty, paid=i.paid)
               for i in order.items],
    )


# koje vremensko polje se popunjava pri kojoj tranziciji
STATUS_TIMESTAMP = {
    "ACCEPTED": "accepted_at",
    "READY": "ready_at",
    "DELIVERED": "delivered_at",
    "CANCELLED": "cancelled_at",
}


async def _notify_barkds(order: Order) -> None:
    """Objavljuje 'order.created' na Kafka topic. (Faza 4: bilo direktan HTTP poziv
    ka barkds-u; sad je asinhroni događaj — barkds ga konzumira svojim tempom.)"""
    await publish_order_event({
        "type": "order.created",
        "order_id": str(order.id),
        "cafe_id": order.cafe_id,
        "table_number": order.table_number,
        "status": order.status,
        "note": order.note,
        "created_at": order.created_at.isoformat(),
        "items": [{"name": i.name, "qty": i.qty} for i in order.items],
    })


async def _notify_barkds_status(order_id: uuid.UUID, status: str) -> None:
    """Objavljuje promenu statusa koju je pokrenuo orders (npr. gostovo otkazivanje)
    kao Kafka događaj 'order.<status>' (npr. order.cancelled) — barkds skida tiket."""
    await publish_order_event({
        "type": f"order.{status.lower()}",
        "order_id": str(order_id),
        "status": status,
    })


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


@router.get("/orders/history", response_model=list[OrderOut])
async def order_history(cafe_id: str, limit: int = 100,
                        session: AsyncSession = Depends(get_session)):
    """Arhiva smene — završene porudžbine (isporučene/otkazane), najnovije prve.
    Osnova za bilans smene: pazar, vreme pripreme, način plaćanja, ocene.
    Definisano PRE /orders/{order_id} da 'history' ne bi bilo tumačeno kao UUID."""
    result = await session.execute(
        select(Order)
        .where(Order.cafe_id == cafe_id,
               Order.status.in_(["DELIVERED", "CANCELLED"]))
        .order_by(Order.created_at.desc())
        .limit(max(1, min(limit, 500)))
    )
    return [_order_out(o) for o in result.scalars().all()]


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_out(order)


@router.get("/tables/{cafe_id}/{table_number}/orders", response_model=list[OrderOut])
async def table_orders(cafe_id: str, table_number: int, sig: str,
                       session: AsyncSession = Depends(get_session)):
    """Porudžbine stola — gost vidi samo svoj sto (potpis iz QR-a). Aktivne +
    skoro isporučene (da može da oceni), bez otkazanih."""
    if not verify_table_signature(cafe_id, table_number, sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")
    cutoff = datetime.now(timezone.utc) - DELIVERED_VISIBLE
    result = await session.execute(
        select(Order)
        .where(Order.cafe_id == cafe_id, Order.table_number == table_number,
               Order.status != "CANCELLED",
               or_(Order.status != "DELIVERED", Order.delivered_at >= cutoff))
        .order_by(Order.created_at.desc())
    )
    return [_order_out(o) for o in result.scalars().all()]


@router.get("/tables/{cafe_id}/{table_number}/bill", response_model=BillOut)
async def table_bill(cafe_id: str, table_number: int, sig: str,
                     session: AsyncSession = Depends(get_session)):
    """Zbirni račun stola — sve stavke svih ne-otkazanih porudžbina u jedan pregled
    (osnova za podelu računa). Potpis stola dokazuje ko gleda."""
    if not verify_table_signature(cafe_id, table_number, sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")
    result = await session.execute(
        select(Order)
        .where(Order.cafe_id == cafe_id, Order.table_number == table_number,
               Order.status != "CANCELLED")
        .order_by(Order.created_at)
    )
    items: list[BillItemOut] = []
    subtotal = paid_total = 0
    for order in result.scalars().all():
        for i in order.items:
            line = i.unit_price * i.qty
            subtotal += line
            if i.paid:
                paid_total += line
            items.append(BillItemOut(order_item_id=i.id, name=i.name,
                                     unit_price=i.unit_price, qty=i.qty,
                                     line_total=line, paid=i.paid))
    return BillOut(cafe_id=cafe_id, table_number=table_number, items=items,
                   subtotal=subtotal, paid_total=paid_total,
                   remaining=subtotal - paid_total)


@router.post("/tables/{cafe_id}/{table_number}/bill/settle", response_model=BillOut)
async def settle_items(cafe_id: str, table_number: int, body: SettleIn,
                       session: AsyncSession = Depends(get_session)):
    """Konobar naplaćuje izabrane stavke (keš/kartica na licu mesta) → obeležava ih
    plaćenim i one otpadaju sa računa. Staff akcija (bez potpisa; zaključati iza Auth-a)."""
    result = await session.execute(
        select(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(OrderItem.id.in_(body.order_item_ids),
               Order.cafe_id == cafe_id, Order.table_number == table_number)
    )
    order_ids: set[uuid.UUID] = set()
    for item in result.scalars().all():
        item.paid = True
        order_ids.add(item.order_id)
    # beleži način plaćanja na porudžbinama tih stavki (best-effort za arhivu)
    if body.payment_method and order_ids:
        await session.execute(
            update(Order).where(Order.id.in_(order_ids))
            .values(payment_method=body.payment_method)
        )
    await session.commit()
    return await table_bill(cafe_id, table_number,
                            sig=table_signature(cafe_id, table_number),
                            session=session)


@router.post("/orders/{order_id}/rating", response_model=OrderOut)
async def rate_order(order_id: uuid.UUID, body: RatingIn,
                     session: AsyncSession = Depends(get_session)):
    """Gost ocenjuje porudžbinu posle isporuke (potpis stola dokazuje ko ocenjuje)."""
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if not verify_table_signature(order.cafe_id, order.table_number, body.sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")
    if order.status != "DELIVERED":
        raise HTTPException(status_code=409, detail="Order not delivered yet")
    order.rating = body.rating
    order.rating_comment = body.comment
    await session.commit()
    return _order_out(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(order_id: uuid.UUID, body: CancelIn,
                       session: AsyncSession = Depends(get_session)):
    """Gost otkazuje SVOJU porudžbinu dok još nije prihvaćena (status CREATED).
    Atomski CAS `WHERE status='CREATED'` rešava trku sa konobarovim prihvatanjem."""
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if not verify_table_signature(order.cafe_id, order.table_number, body.sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")
    result = await session.execute(
        update(Order)
        .where(Order.id == order_id, Order.status == "CREATED")
        .values(status="CANCELLED", cancelled_at=datetime.now(timezone.utc))
    )
    if result.rowcount == 0:
        # neko je stigao prvi: konobar je prihvatio ili je već otkazano
        raise HTTPException(status_code=409,
                            detail="Order already accepted or cancelled")
    await session.commit()
    await session.refresh(order)
    await _notify_barkds_status(order_id, "CANCELLED")
    return _order_out(order)


@router.patch("/internal/orders/{order_id}/status", response_model=OrderOut)
async def update_status(order_id: uuid.UUID, body: StatusUpdate,
                        session: AsyncSession = Depends(get_session)):
    """Interna ruta — Bar/KDS javlja promenu statusa. Tranzicija se izvodi atomski
    (`WHERE status=<trenutni>`) da bi bila bezbedna uz gostovu cancel rutu."""
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    current = order.status
    if body.status not in STATUS_FLOW.get(current, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition {current} -> {body.status}",
        )
    values: dict = {"status": body.status,
                    STATUS_TIMESTAMP[body.status]: datetime.now(timezone.utc)}
    if body.taken_by:
        values["taken_by"] = body.taken_by
    if body.payment_method:
        values["payment_method"] = body.payment_method
    result = await session.execute(
        update(Order).where(Order.id == order_id, Order.status == current)
        .values(**values)
    )
    if result.rowcount == 0:
        # status se promenio između čitanja i pisanja (npr. gost otkazao u međuvremenu)
        raise HTTPException(status_code=409, detail="Order changed concurrently")
    await session.commit()
    await session.refresh(order)
    return _order_out(order)


if settings.app_env == "dev":
    @router.get("/dev/sign")
    def dev_sign(cafe_id: str, table_number: int):
        """Pomoćna dev ruta: generiše QR potpis stola (nedostupna kroz gateway)."""
        return {"cafe_id": cafe_id, "table_number": table_number,
                "sig": table_signature(cafe_id, table_number)}
